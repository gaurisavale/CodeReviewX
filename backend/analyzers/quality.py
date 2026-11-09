"""Rule based quality detectors. Every finding carries exact line evidence."""
from __future__ import annotations

import ast
import builtins
import difflib
import re
from typing import Dict, List, Optional

from .structural import (FUNC_TYPES, FuncInfo, ModuleInfo, SCOPE_BREAK, ancestors, call_name,
                         dotted, param_names, stored_names, walk_scope)

ALLOWED_NUMBERS = {0, 1, 2, -1, 100}
SHORT_OK = {"i", "j", "k", "_", "id", "ok", "db", "fn", "e", "f", "cb", "tx"}
VAGUE = {"data", "tmp", "temp", "val", "res", "ret", "obj", "thing", "stuff", "foo", "bar", "baz", "var", "lst", "arr", "dd"}
IO_NAMES = {"print", "input", "open"}
SIDE_EFFECT_PREFIX = ("save", "write", "insert", "update", "commit", "send", "delete", "store", "persist", "reserve", "charge", "refund", "emit", "publish", "execute")
RISKY_PREFIX = SIDE_EFFECT_PREFIX + ("load", "read", "fetch", "connect", "request", "post", "get_from", "download", "upload", "validate_payment", "process_payment")
RISKY_ATTRS = {"loads", "load", "post", "put", "request", "connect", "execute", "commit", "sendmail", "urlopen", "read", "write", "send", "insert", "dump", "dumps"}
SECRET_RE = re.compile(r"(password|passwd|secret|token|api_?key|private_?key)", re.I)


def _lines_of(nodes) -> List[int]:
    return sorted({n.lineno for n in nodes if hasattr(n, "lineno")})


def _snippet(mod: ModuleInfo, a: int, b: int, limit: int = 6) -> str:
    seg = mod.src_lines[a - 1:b]
    if len(seg) > limit:
        seg = seg[:limit] + ["..."]
    return "\n".join(seg)


def _span(lines: List[int]) -> tuple:
    return (min(lines), max(lines)) if lines else (1, 1)


def _fmt_lines(lines: List[int], n: int = 6) -> str:
    s = ", ".join(str(x) for x in lines[:n])
    return s + (" ..." if len(lines) > n else "")


def make(mod: ModuleInfo, fn: FuncInfo, factor: str, rule: str, severity: str, title: str,
         lines: List[int], metric_label: str, metric_value: str, why: str, rec: str,
         auto_fix: Optional[str] = None) -> Dict:
    lines = sorted(set(lines)) or [fn.line_start]
    a, b = _span(lines)
    # for single contiguous evidence show the block, else show first line
    if len(lines) == 1 and rule in ("long_function", "complexity", "elif_chain", "deep_nesting", "duplication", "repeated_branches", "many_params"):
        b = max(b, lines[0])
    return {
        "factor": factor, "rule": rule, "severity": severity, "title": title,
        "function": fn.name, "line_start": a, "line_end": b, "lines": lines,
        "evidence": _snippet(mod, a, min(b, a + 5)),
        "metric_label": metric_label, "metric_value": metric_value,
        "why": why, "recommendation": rec, "auto_fix": auto_fix,
    }


# ------------------------------------------------------------- data gathering
def _scope_info(mod: ModuleInfo, fn: FuncInfo) -> Dict:
    node = fn.node
    nodes = list(walk_scope(node))
    nodes.sort(key=lambda n: (getattr(n, "lineno", 0), getattr(n, "col_offset", 0)))
    calls = [n for n in nodes if isinstance(n, ast.Call)]
    return {"nodes": nodes, "calls": calls}


def _in_args(n: ast.AST) -> bool:
    return any(isinstance(a, ast.arguments) for a in ancestors(n))


# ------------------------------------------------------------------ detectors
def d_metrics(mod, fn, ctx):
    out = []
    cx = fn.complexity
    if cx >= 10:
        sev = "critical" if cx >= 20 else "warning"
        out.append(make(mod, fn, "complexity", "complexity", sev, "High cyclomatic complexity",
                        [fn.line_start], "Cyclomatic / cognitive", f"{cx} / {fn.cognitive}",
                        f"{fn.name} has {cx} independent paths (cognitive score {fn.cognitive}). Every path needs its own test and a reader must hold all of them in their head.",
                        "Split the function by responsibility so each piece has fewer than 10 paths.", "extract_method"))
    if fn.elif_len >= 4:
        out.append(make(mod, fn, "complexity", "elif_chain", "warning", f"Long if/elif chain ({fn.elif_len} branches)",
                        list(range(fn.elif_start, fn.elif_start + 1)), "Branches", str(fn.elif_len),
                        f"A chain of {fn.elif_len} branches on lines {fn.elif_start}-{fn.elif_end} hard-codes a decision table inside control flow. Each new case grows the chain and the risk of ordering bugs.",
                        "Move the cases into a lookup table or a small classifier function that returns early.", "extract_method"))
    if fn.nesting >= 3:
        sev = "critical" if fn.nesting >= 5 else "warning" if fn.nesting >= 4 else "info"
        out.append(make(mod, fn, "nesting", "deep_nesting", sev, "Deeply nested logic",
                        [fn.nesting_line or fn.line_start], "Max nesting", str(fn.nesting),
                        f"Control flow nests {fn.nesting} levels deep (deepest block starts on line {fn.nesting_line}). Deep nesting hides the happy path and multiplies edge cases.",
                        "Use guard clauses (return early on invalid or trivial cases) and extract inner blocks.", "guard_clause"))
    if fn.lines >= 30:
        sev = "critical" if fn.lines >= 100 else "warning" if fn.lines >= 50 else "info"
        out.append(make(mod, fn, "length", "long_function", sev, "Long function",
                        [fn.line_start], "Lines", str(fn.lines),
                        f"{fn.name} spans {fn.lines} lines (lines {fn.line_start}-{fn.line_end}). Long functions usually mix several jobs and are hard to review in one sitting.",
                        "Extract cohesive blocks into small named helpers (aim for under 30 lines).", "extract_method"))
    if fn.param_count >= 5:
        sev = "critical" if fn.param_count >= 8 else "warning"
        names = ", ".join(p for p in fn.params if p not in ("self", "cls"))
        out.append(make(mod, fn, "parameters", "many_params", sev, "Too many parameters",
                        [fn.line_start], "Parameters", str(fn.param_count),
                        f"Signature takes {fn.param_count} parameters ({names}). Callers must remember the order and the function usually does too much.",
                        "Group related values into a dataclass / dict, or split the function.", None))
    return out


def d_naming(mod, fn, ctx):
    tiny = fn.lines <= 5
    ok = SHORT_OK | ({"x", "y", "z", "n", "a", "b"} if tiny else set())
    bad: Dict[str, int] = {}
    for p in fn.params:
        if p not in ("self", "cls") and (len(p) <= 2 and p not in ok or p in VAGUE):
            bad.setdefault(p, fn.node.lineno)
    for n in ctx["nodes"]:
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            nm = n.id
            if (len(nm) <= 2 and nm not in ok) or nm in VAGUE:
                bad.setdefault(nm, n.lineno)
    if not bad:
        return []
    sev = "warning" if len(bad) >= 3 else "info"
    names = ", ".join(f"`{k}`" for k in list(bad)[:8])
    return [make(mod, fn, "naming", "poor_names", sev, "Poor variable names", list(bad.values()),
                 "Unclear names", str(len(bad)),
                 f"Single-letter or vague names ({names}) force the reader to guess meaning from usage. In {fn.name} this hides what each value represents (units, domain meaning).",
                 "Rename to intention-revealing names, e.g. `weight_kg`, `heart_rate_bpm`, `order_total`.", None)]


def d_magic(mod, fn, ctx):
    thresholds, magics = [], []
    for n in ctx["nodes"]:
        if not isinstance(n, ast.Constant) or isinstance(n.value, bool) or not isinstance(n.value, (int, float)):
            continue
        if n.value in ALLOWED_NUMBERS or _in_args(n):
            continue
        par = getattr(n, "_parent", None)
        if isinstance(par, ast.UnaryOp):
            par = getattr(par, "_parent", None)
        if isinstance(par, ast.Subscript) or (isinstance(par, ast.Call) and call_name(par) == "round"):
            continue
        if isinstance(par, ast.Assign) and all(isinstance(t, ast.Name) and t.id.isupper() for t in par.targets):
            continue
        if isinstance(par, ast.Compare):
            thresholds.append(n)
        else:
            magics.append(n)
    out = []
    if thresholds:
        vals = sorted({repr(t.value) for t in thresholds}, key=lambda s: float(s))
        sev = "warning" if len(thresholds) >= 3 else "info"
        out.append(make(mod, fn, "magic_numbers", "hardcoded_thresholds", sev, "Hard-coded thresholds in conditions",
                        _lines_of(thresholds), "Thresholds", f"{len(thresholds)} ({', '.join(vals[:6])})",
                        f"Conditions compare against raw numbers ({', '.join(vals[:6])}). Nobody can tell whether they are policy, medical limits or guesses, and changing one means hunting through the code.",
                        "Hoist each threshold into a named constant (e.g. `BMI_UNDERWEIGHT_LIMIT = 18.5`) or a config table.", "constants"))
    if magics:
        vals = sorted({repr(t.value) for t in magics}, key=lambda s: float(s))
        sev = "warning" if len(magics) >= 3 else "info"
        out.append(make(mod, fn, "magic_numbers", "magic_numbers", sev, "Magic numbers in expressions",
                        _lines_of(magics), "Magic numbers", f"{len(magics)} ({', '.join(vals[:6])})",
                        f"Unexplained literals ({', '.join(vals[:6])}) appear inside calculations, so their meaning (rate, unit, limit) is lost.",
                        "Give each literal a descriptive constant name next to the function or in a config module.", None))
    return out


def _risky_ops(fn: FuncInfo, ctx):
    ops = []
    params = set(fn.params)
    for n in ctx["nodes"]:
        if isinstance(n, ast.Call):
            nm = call_name(n)
            if not nm:
                continue
            if isinstance(n.func, ast.Name) and nm in ("open", "int", "float"):
                ops.append((n.lineno, f"{nm}()"))
            elif isinstance(n.func, ast.Name) and nm.startswith(RISKY_PREFIX):
                ops.append((n.lineno, f"{nm}()"))
            elif isinstance(n.func, ast.Attribute) and (nm in RISKY_ATTRS or nm.startswith(RISKY_PREFIX)):
                ops.append((n.lineno, f"{dotted(n.func)}()"))
        elif isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            r = n.right
            if not (isinstance(r, ast.Constant) and r.value not in (0, None)):
                ops.append((n.lineno, "division"))
        elif isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id in params:
            if isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str):
                ops.append((n.lineno, f'{n.value.id}["{n.slice.value}"]'))
    return ops


def d_errors(mod, fn, ctx):
    out = []
    tries = [n for n in ctx["nodes"] if isinstance(n, ast.Try)]
    ops = _risky_ops(fn, ctx)
    if ops and not tries:
        kinds = sorted({o[1] for o in ops})
        out.append(make(mod, fn, "error_handling", "no_exception_handling", "warning", "No exception handling around risky operations",
                        [o[0] for o in ops], "Risky ops / try blocks", f"{len(ops)} / 0",
                        f"{fn.name} performs operations that can fail ({', '.join(kinds[:5])}) with no try/except. One bad input or an I/O failure will crash the caller with no context.",
                        "Wrap the failing operations, catch specific exceptions, and raise a meaningful error or return a clear result.", None))
    for t in tries:
        for h in t.handlers:
            broad = h.type is None or (isinstance(h.type, ast.Name) and h.type.id in ("Exception", "BaseException"))
            silent = all(isinstance(s, (ast.Pass, ast.Continue)) for s in h.body)
            if h.type is None or (broad and silent):
                out.append(make(mod, fn, "error_handling", "swallowed_exception", "warning", "Bare or swallowed exception",
                                [h.lineno], "Handler", "bare except" if h.type is None else "except Exception: pass",
                                "A bare/over-broad except that does nothing hides real bugs and makes failures invisible.",
                                "Catch the specific exception types you expect and log or re-raise.", None))
    return out


def _has_validation(fn: FuncInfo, ctx) -> bool:
    params = set(fn.params)
    for n in ctx["nodes"]:
        if isinstance(n, (ast.Raise, ast.Assert)):
            return True
        if isinstance(n, ast.Call) and call_name(n) in ("isinstance", "issubclass", "validate", "check", "ensure"):
            return True
    for st in fn.node.body[:5]:
        if isinstance(st, ast.If):
            names = {x.id for x in ast.walk(st.test) if isinstance(x, ast.Name)}
            if names & params and st.body and isinstance(st.body[-1], (ast.Return, ast.Raise)):
                return True
    return False


def d_validation(mod, fn, ctx):
    if fn.param_count == 0 or fn.simple_name.startswith("_") or fn.lines < 6:
        return []
    if _has_validation(fn, ctx):
        return []
    sev = "warning" if fn.param_count >= 2 else "info"
    names = ", ".join(f"`{p}`" for p in fn.params if p not in ("self", "cls"))
    return [make(mod, fn, "validation", "no_validation", sev, "No input validation",
                 [fn.line_start], "Validated params", f"0 / {fn.param_count}",
                 f"{fn.name} trusts every parameter ({names}). There is no type, range, None or emptiness check, so bad data flows straight into the logic (wrong output or a crash far from the cause).",
                 "Validate at the top: check types and ranges, raise ValueError/TypeError with a clear message, or return early.", None)]


def _resp(mod, fn, ctx) -> Dict[str, List[int]]:
    r: Dict[str, List[int]] = {}
    arith = 0
    jstr = []
    for n in ctx["nodes"]:
        if isinstance(n, ast.Call):
            nm = call_name(n)
            if isinstance(n.func, ast.Name) and nm in ("print", "input"):
                r.setdefault("console I/O", []).append(n.lineno)
            elif nm and (nm.startswith(SIDE_EFFECT_PREFIX)):
                r.setdefault("persistence / side effects", []).append(n.lineno)
        elif isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv)):
            if not (isinstance(n.left, ast.Constant) and isinstance(n.left.value, str)):
                arith += 1
                r.setdefault("calculation", []).append(n.lineno)
        elif isinstance(n, ast.JoinedStr):
            jstr.append(n.lineno)
        elif isinstance(n, (ast.Raise, ast.Assert)):
            r.setdefault("validation", []).append(n.lineno)
    if arith < 2 and "calculation" in r:
        del r["calculation"]
    if len(jstr) >= 2:
        r["formatting"] = jstr
    if fn.elif_len >= 3 or fn.complexity >= 6:
        r["decision logic"] = [fn.elif_start or fn.line_start]
    if "validation" not in r and _has_validation(fn, ctx):
        r["validation"] = [fn.line_start]
    return r


def d_separation(mod, fn, ctx):
    out = []
    resp = _resp(mod, fn, ctx)
    fn_resp = resp
    prints = fn_resp.get("console I/O", [])
    name = fn.simple_name.lower()
    presentational = name.startswith(("print", "show", "display", "report", "render", "main", "cli", "run"))
    logic = bool(fn_resp.get("calculation")) or fn.complexity >= 4
    if prints and logic and not (presentational and fn.complexity < 6):
        sev = "warning" if len(prints) >= 2 else "info"
        out.append(make(mod, fn, "separation", "io_mixed", sev, "print()/input() mixed with business logic",
                        prints, "Console calls", str(len(prints)),
                        f"{fn.name} both decides things and talks to the console ({len(prints)} calls). It cannot be unit-tested without capturing stdout and cannot be reused from an API or UI.",
                        "Return data from the logic function and let a thin presentation layer print or render it.", "extract_method"))
    if len(resp) >= 3 and fn.lines >= 12:
        sev = "warning"
        out.append(make(mod, fn, "separation", "multiple_responsibilities", sev, "Multiple responsibilities in one function",
                        [min(v) for v in resp.values()], "Responsibilities", f"{len(resp)} ({', '.join(sorted(resp))})",
                        f"{fn.name} handles {len(resp)} distinct jobs: {', '.join(sorted(resp))}. A change to any one of them risks breaking the others (Single Responsibility Principle).",
                        "Split by job: validate, compute, persist and present each in their own function.", "extract_method"))
    fn_resp_store = {k: sorted(set(v)) for k, v in resp.items()}
    ctx["responsibilities"] = fn_resp_store
    return out


def d_doc(mod, fn, ctx):
    if not fn.has_docstring and fn.lines >= 8 and not fn.simple_name.startswith("_"):
        return [make(mod, fn, "documentation", "missing_docstring", "info", "Missing docstring",
                     [fn.line_start], "Docstring", "none",
                     f"{fn.name} ({fn.lines} lines) has no docstring, so its contract (inputs, outputs, side effects) is undocumented.",
                     "Add a short docstring: purpose, parameters, return value, raised errors.", None)]
    return []


def d_correctness(mod, fn, ctx):
    out = []
    node = fn.node
    defined = set(fn.params) | stored_names(node) | set(mod.global_names) | set(dir(builtins))
    for enc in fn.enclosing:
        defined |= set(param_names(enc)) | stored_names(enc)
    defined |= {"__file__", "__name__", "__class__"}
    undefined: Dict[str, int] = {}
    for n in ctx["nodes"]:
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in defined:
            undefined.setdefault(n.id, n.lineno)
    for nm, ln in undefined.items():
        hints = [p for p in fn.params if p not in ("self", "cls")]
        cand = difflib.get_close_matches(nm, hints, n=1, cutoff=0.6) or [p for p in hints if len(p) <= 2 and nm.startswith(p)]
        extra = f" Did you mean the parameter `{cand[0]}`?" if cand else ""
        out.append(make(mod, fn, "correctness", "undefined_name", "critical", f"Undefined name `{nm}` (runtime bug)",
                        [ln], "Undefined reads", nm,
                        f"`{nm}` is read on line {ln} but is never defined in {fn.name} or at module level, so this line raises NameError whenever it executes.{extra}",
                        f"Define `{nm}` or pass it in as a parameter." + (f" Likely fix: use `{cand[0]}`." if cand else ""), None))
    # mutable defaults
    a = node.args
    for d in list(a.defaults) + [x for x in a.kw_defaults if x is not None]:
        if isinstance(d, (ast.List, ast.Dict, ast.Set)):
            out.append(make(mod, fn, "correctness", "mutable_default", "warning", "Mutable default argument",
                            [d.lineno], "Default", type(d).__name__.lower(),
                            "A list/dict/set default is created once and shared by every call, which leaks state between calls.",
                            "Use `None` as the default and create the container inside the function.", None))
    # unreachable code
    for n in ctx["nodes"] + [node]:
        for fld in ("body", "orelse", "finalbody"):
            seq = getattr(n, fld, None)
            if isinstance(seq, list):
                for i, st in enumerate(seq[:-1]):
                    if isinstance(st, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                        nxt = seq[i + 1]
                        out.append(make(mod, fn, "correctness", "unreachable_code", "warning", "Unreachable code",
                                        [nxt.lineno], "Dead lines", "1+",
                                        f"Statements after the `{type(st).__name__.lower()}` on line {st.lineno} can never run.",
                                        "Delete the dead code or fix the control flow that makes it unreachable.", None))
                        break
    # == None
    nn = [n for n in ctx["nodes"] if isinstance(n, ast.Compare) and any(isinstance(o, (ast.Eq, ast.NotEq)) for o in n.ops)
          and any(isinstance(c, ast.Constant) and c.value is None for c in n.comparators)]
    if nn:
        out.append(make(mod, fn, "correctness", "none_compare", "info", "Comparison to None with == / !=",
                        _lines_of(nn), "Occurrences", str(len(nn)),
                        "`== None` can be overridden by objects and is not idiomatic.", "Use `is None` / `is not None`.", None))
    # unused params / locals
    loads = {n.id for n in ctx["nodes"] if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    body_trivial = all(isinstance(s, (ast.Pass, ast.Raise, ast.Expr)) for s in node.body)
    unused_p = [p for p in fn.params if p not in ("self", "cls") and not p.startswith("_") and p not in loads]
    if unused_p and not body_trivial:
        out.append(make(mod, fn, "correctness", "unused_param", "info", "Unused parameters",
                        [node.lineno], "Unused", ", ".join(unused_p),
                        f"Parameters {', '.join('`'+p+'`' for p in unused_p)} are never read, which suggests a bug or a stale signature.",
                        "Remove them or use them.", None))
    stores: Dict[str, int] = {}
    for n in ctx["nodes"]:
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and not n.id.startswith("_"):
            stores.setdefault(n.id, n.lineno)
    glob = {x for g in ctx["nodes"] if isinstance(g, (ast.Global, ast.Nonlocal)) for x in g.names}
    unused_l = [k for k in stores if k not in loads and k not in glob and k not in fn.params]
    if unused_l:
        out.append(make(mod, fn, "correctness", "unused_local", "info", "Variables assigned but never used",
                        [stores[k] for k in unused_l], "Unused", ", ".join(unused_l[:6]),
                        f"{', '.join('`'+k+'`' for k in unused_l[:6])} are assigned but never read. Either dead code or a missing use (possible bug).",
                        "Remove them or use the value.", None))
    return out


def d_security(mod, fn, ctx):
    out = []
    for n in ctx["nodes"]:
        if isinstance(n, ast.Call):
            nm = call_name(n)
            full = dotted(n.func) if isinstance(n.func, ast.Attribute) else (nm or "")
            if isinstance(n.func, ast.Name) and nm in ("eval", "exec"):
                out.append(make(mod, fn, "security", "eval_exec", "critical", f"Use of {nm}()", [n.lineno], "Call", f"{nm}()",
                                f"`{nm}()` executes arbitrary code. If any input reaches it, an attacker controls the process.",
                                "Use `ast.literal_eval`, a parser, or an explicit dispatch table.", None))
            elif full in ("os.system", "os.popen") or (full.startswith("subprocess.") and any(
                    k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True for k in n.keywords)):
                out.append(make(mod, fn, "security", "shell_exec", "critical", "Shell command execution", [n.lineno], "Call", full,
                                "Commands built as shell strings allow command injection.",
                                "Use `subprocess.run([...])` with a list of arguments and `shell=False`.", None))
            elif full in ("pickle.loads", "pickle.load", "yaml.load", "marshal.loads"):
                out.append(make(mod, fn, "security", "unsafe_deserialization", "warning", "Unsafe deserialization", [n.lineno], "Call", full,
                                "Deserializing untrusted data with this API can execute code.", "Use JSON or `yaml.safe_load`.", None))
            elif nm in ("execute", "executemany") and n.args:
                a0 = n.args[0]
                if isinstance(a0, (ast.JoinedStr, ast.BinOp)) or (isinstance(a0, ast.Call) and call_name(a0) == "format"):
                    out.append(make(mod, fn, "security", "sql_injection", "critical", "SQL built from strings", [n.lineno], "Call", f"{nm}(<string>)",
                                    "Building SQL with f-strings/concatenation enables SQL injection.", "Use parameterised queries (`execute(sql, params)`).", None))
            for k in n.keywords:
                if k.arg == "verify" and isinstance(k.value, ast.Constant) and k.value.value is False:
                    out.append(make(mod, fn, "security", "tls_verify_off", "warning", "TLS verification disabled", [n.lineno], "Argument", "verify=False",
                                    "Disabling certificate verification allows man-in-the-middle attacks.", "Remove `verify=False`.", None))
        elif isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str) and len(n.value.value) >= 4:
            for t in n.targets:
                if isinstance(t, ast.Name) and SECRET_RE.search(t.id):
                    out.append(make(mod, fn, "security", "hardcoded_secret", "warning", "Hard-coded secret", [n.lineno], "Variable", t.id,
                                    f"`{t.id}` holds a literal credential in source code, which leaks through version control.",
                                    "Load secrets from environment variables or a secret manager.", None))
    return out


# --------------------------------------------------------------- duplication
class _Norm(ast.NodeTransformer):
    def visit_Name(self, n):
        return ast.copy_location(ast.Name(id="_", ctx=n.ctx), n)

    def visit_Constant(self, n):
        return ast.copy_location(ast.Constant(value=type(n.value).__name__), n)

    def visit_arg(self, n):
        return ast.copy_location(ast.arg(arg="_"), n)


def _ser(n) -> str:
    """Structural fingerprint without copying the tree: names and constants are abstracted."""
    if isinstance(n, ast.AST):
        if isinstance(n, ast.Name):
            return "N" + type(n.ctx).__name__
        if isinstance(n, ast.Constant):
            return "C:" + type(n.value).__name__
        if isinstance(n, ast.arg):
            return "arg"
        return type(n).__name__ + "(" + ",".join(_ser(getattr(n, f, None)) for f in n._fields) + ")"
    if isinstance(n, list):
        return "[" + ",".join(_ser(x) for x in n) + "]"
    return repr(n)


def _fp(stmts) -> str:
    return _ser(list(stmts))


def _size(stmts) -> int:
    return sum(1 for s in stmts for _ in ast.walk(s))


def _owner(mod: ModuleInfo, lineno: int) -> Optional[FuncInfo]:
    best = None
    for f in mod.functions:
        if f.line_start <= lineno <= f.line_end and (best is None or f.line_start >= best.line_start):
            best = f
    return best


def detect_duplication(mod: ModuleInfo) -> Dict[str, List[Dict]]:
    out: Dict[str, List[Dict]] = {f.name: [] for f in mod.functions}
    groups: Dict[str, List[tuple]] = {}
    for f in mod.functions:
        for n in walk_scope(f.node):
            cands = []
            if isinstance(n, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                cands.append(([n], n))
            if isinstance(n, ast.If):
                cands.append((n.body, n))
            for stmts, anchor in cands:
                if _size(stmts) >= 14:
                    a, b = stmts[0].lineno, stmts[-1].end_lineno or stmts[-1].lineno
                    groups.setdefault(_fp(stmts), []).append((f, a, b))
    claimed = []
    for fp, occ in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        uniq = []
        for f, a, b in sorted(occ, key=lambda o: o[1]):
            if not any(a == x[1] and b == x[2] for x in uniq):
                uniq.append((f, a, b))
        # drop overlapping occurrences within same group (nested)
        flt = []
        for o in uniq:
            if not any(p[0] is o[0] and p[1] <= o[1] and o[2] <= p[2] and p is not o for p in uniq):
                flt.append(o)
        uniq = flt
        if len(uniq) < 2:
            continue
        if any(_overlap(uniq, claimed)):
            continue
        claimed += uniq
        involved = {}
        for f, a, b in uniq:
            involved.setdefault(f.name, []).append((a, b))
        for fname, spans in involved.items():
            f = next(x for x in mod.functions if x.name == fname)
            others = sorted({o[0].name for o in uniq if o[0].name != fname})
            where = f"also in {', '.join(others)}" if others else "repeated inside this function"
            lines = [a for a, _ in spans]
            out[fname].append(make(mod, f, "duplication", "duplication", "warning", f"Duplicated logic ({len(uniq)} copies)",
                                   lines, "Copies", str(len(uniq)),
                                   f"The same statement structure appears {len(uniq)} times ({where}); lines {_fmt_lines(lines)} here. Copies drift apart and a bug fix has to be repeated everywhere.",
                                   "Extract the shared logic into one helper and call it from each place.", "extract_method"))
    # repeated if/elif branch shape
    for f in mod.functions:
        for n in walk_scope(f.node):
            if isinstance(n, ast.If) and not _elif(n):
                branches, cur = [], n
                while True:
                    branches.append(cur.body)
                    if len(cur.orelse) == 1 and isinstance(cur.orelse[0], ast.If):
                        cur = cur.orelse[0]
                    else:
                        if cur.orelse:
                            branches.append(cur.orelse)
                        break
                if len(branches) >= 3:
                    fps: Dict[str, int] = {}
                    for b in branches:
                        fps[_fp(b)] = fps.get(_fp(b), 0) + 1
                    top = max(fps.values())
                    if top >= 3:
                        sev = "warning" if top >= 4 else "info"
                        out[f.name].append(make(mod, f, "duplication", "repeated_branches", sev, f"Repeated if/elif branch shape ({top} of {len(branches)})",
                                                [n.lineno], "Same-shape branches", f"{top} / {len(branches)}",
                                                f"{top} branches of the chain on line {n.lineno} have identical structure and differ only in constants, a sign the chain is really data.",
                                                "Replace the chain with a lookup table (list of (limit, label)) and a loop.", "extract_method"))
    return out


def _elif(n: ast.If) -> bool:
    p = getattr(n, "_parent", None)
    return isinstance(p, ast.If) and len(p.orelse) == 1 and p.orelse[0] is n


def _overlap(uniq, claimed):
    for f, a, b in uniq:
        for g, c, d in claimed:
            yield f is g and not (b < c or d < a)


DETECTORS = [d_metrics, d_naming, d_magic, d_errors, d_validation, d_separation, d_doc, d_correctness, d_security]


def run_detectors(mod: ModuleInfo) -> Dict[str, Dict]:
    """Returns {function name: {"findings": [...], "responsibilities": {...}}}."""
    dup = detect_duplication(mod)
    res = {}
    for fn in mod.functions:
        ctx = _scope_info(mod, fn)
        findings: List[Dict] = []
        for d in DETECTORS:
            findings += d(mod, fn, ctx)
        findings += dup.get(fn.name, [])
        res[fn.name] = {"findings": findings, "responsibilities": ctx.get("responsibilities", {})}
    return res
