"""Automated, verifiable refactoring.

Three safe transformations, all built on the AST:
  1. constants    : hard-coded comparison thresholds -> named module constants
  2. guard clause : trailing `if cond: <nested block>` -> early return
  3. extract      : big branch blocks / print runs -> helper functions, using
                    data-flow (inputs = defined-before & used, outputs = set & used-later)
Anything that cannot be proven safe is skipped. The result is re-parsed.
"""
from __future__ import annotations

import ast
import copy
import re
from typing import Dict, List, Optional, Set, Tuple

from analyzers.structural import FUNC_TYPES, FuncInfo, ModuleInfo, walk_scope

INVERT = {ast.Lt: ast.GtE, ast.LtE: ast.Gt, ast.Gt: ast.LtE, ast.GtE: ast.Lt, ast.Eq: ast.NotEq,
          ast.NotEq: ast.Eq, ast.Is: ast.IsNot, ast.IsNot: ast.Is, ast.In: ast.NotIn, ast.NotIn: ast.In}
ALLOWED = {0, 1, 2, -1, 100}
BAD_IN_UNIT = (ast.Return, ast.Yield, ast.YieldFrom, ast.Await, ast.Global, ast.Nonlocal, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _negate(test: ast.expr) -> ast.expr:
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and type(test.ops[0]) in INVERT:
        return ast.Compare(left=test.left, ops=[INVERT[type(test.ops[0])]()], comparators=test.comparators)
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return test.operand
    return ast.UnaryOp(op=ast.Not(), operand=test)


def _decisions(n: ast.AST) -> int:
    return sum(isinstance(x, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.IfExp)) for x in ast.walk(n)) + \
        sum(len(x.values) - 1 for x in ast.walk(n) if isinstance(x, ast.BoolOp))


def _has_compound(stmts) -> bool:
    return any(isinstance(x, (ast.If, ast.For, ast.While, ast.Try, ast.With)) for s in stmts for x in ast.walk(s))


def _loads(stmts) -> List[str]:
    seen, out = set(), []
    for s in stmts:
        for n in ast.walk(s):
            nm = None
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                nm = n.id
            elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
                nm = n.target.id
            if nm and nm not in seen:
                seen.add(nm)
                out.append(nm)
    return out


def _stores(stmts) -> List[str]:
    seen, out = set(), []
    for s in stmts:
        for n in ast.walk(s):
            if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)) and n.id not in seen:
                seen.add(n.id)
                out.append(n.id)
    return out


def definite_assigns(stmts) -> Set[str]:
    out: Set[str] = set()
    for s in stmts:
        if isinstance(s, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            for n in ast.walk(s):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                    out.add(n.id)
        elif isinstance(s, ast.If):
            if s.orelse:
                out |= definite_assigns(s.body) & definite_assigns(s.orelse)
        elif isinstance(s, ast.With):
            out |= definite_assigns(s.body)
        elif isinstance(s, (ast.For, ast.While)):
            pass
    return out


def _is_print(s: ast.stmt) -> bool:
    return isinstance(s, ast.Expr) and isinstance(s.value, ast.Call) and isinstance(s.value.func, ast.Name) and s.value.func.id == "print"


# ----------------------------------------------------------------- constants
def hoist_constants(fn: ast.AST, taken: Set[str]) -> Tuple[List[ast.Assign], List[str]]:
    consts: Dict[str, Tuple[str, ast.Constant]] = {}
    notes: List[str] = []
    for cmp_ in [n for n in ast.walk(fn) if isinstance(n, ast.Compare)]:
        operands = [cmp_.left] + list(cmp_.comparators)
        for idx, op in enumerate(operands):
            c = op
            neg = False
            if isinstance(op, ast.UnaryOp) and isinstance(op.op, ast.USub) and isinstance(op.operand, ast.Constant):
                c, neg = op.operand, True
            if not (isinstance(c, ast.Constant) and isinstance(c.value, (int, float)) and not isinstance(c.value, bool)):
                continue
            val = -c.value if neg else c.value
            if val in ALLOWED:
                continue
            other = next((o for j, o in enumerate(operands) if j != idx and isinstance(o, (ast.Name, ast.Attribute, ast.Call))), None)
            if isinstance(other, ast.Call):
                other = other.func if isinstance(other.func, (ast.Name, ast.Attribute)) else None
            base = (other.id if isinstance(other, ast.Name) else other.attr if isinstance(other, ast.Attribute) else "VALUE").upper()
            sval = re.sub(r"[^0-9A-Z]", "_", repr(val).upper().replace("-", "NEG_"))
            name = f"{base}_THRESHOLD_{sval}"
            if name in taken and name not in consts:
                continue
            consts.setdefault(name, (name, ast.Constant(value=val)))
            new = ast.Name(id=name, ctx=ast.Load())
            if idx == 0:
                cmp_.left = new
            else:
                cmp_.comparators[idx - 1] = new
    assigns = [ast.Assign(targets=[ast.Name(id=n, ctx=ast.Store())], value=c, lineno=0) for n, c in sorted(consts.values(), key=lambda kv: kv[0])]
    if assigns:
        notes.append(f"{len(assigns)} hard-coded threshold(s) became named constants")
    return assigns, notes


# ---------------------------------------------------------------- guard clause
def _guard(core: List[ast.stmt], ret: ast.Return) -> Tuple[List[ast.stmt], int]:
    if core and isinstance(core[-1], ast.If) and not core[-1].orelse and _has_compound(core[-1].body):
        last = core[-1]
        rest, n = _guard(last.body, ret)
        guard = ast.If(test=_negate(last.test), body=[copy.deepcopy(ret)], orelse=[])
        return core[:-1] + [guard] + rest, n + 1
    return core, 0


def guardify(body: List[ast.stmt]) -> Tuple[List[ast.stmt], int]:
    """`if A: <nested>` at the end of a function (optionally followed by `return None/const`)
    becomes `if not A: return ...` + the block, one level flatter."""
    tail, core = None, body
    if body and isinstance(body[-1], ast.Return) and (body[-1].value is None or isinstance(body[-1].value, ast.Constant)):
        tail, core = body[-1], body[:-1]
    new, n = _guard(core, tail or ast.Return(value=None))
    if new and isinstance(new[-1], (ast.Return, ast.Raise)):
        return new, n
    return new + ([tail] if tail else []), n


# ---------------------------------------------------------------- extraction
def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", s.lower()).strip("_") or "step"


def _unit_name(kind: str, stmts, outs: List[str], taken: Set[str]) -> str:
    if kind == "report":
        base = "_print_report"
    elif kind == "checks":
        vs = []
        for s in stmts:
            for n in ast.walk(s):
                if isinstance(n, ast.Compare) and isinstance(n.left, ast.Name) and n.left.id not in vs:
                    vs.append(n.left.id)
        base = "_check_" + "_".join(_slug(v) for v in vs[:3]) if 0 < len(vs) <= 3 else "_run_checks"
    elif outs:
        s0 = stmts[0]
        base = ("_classify_" if isinstance(s0, ast.If) else "_compute_" if not isinstance(s0, (ast.For, ast.While)) else "_collect_") + _slug(outs[0])
    elif isinstance(stmts[0], (ast.For, ast.While)):
        tgt = stmts[0].target.id if isinstance(stmts[0], ast.For) and isinstance(stmts[0].target, ast.Name) else "items"
        base = "_process_" + _slug(tgt)
    else:
        vs = [n.left.id for n in ast.walk(stmts[0]) if isinstance(n, ast.Compare) and isinstance(n.left, ast.Name)]
        base = "_check_" + _slug(vs[0]) if vs else "_step"
    name, i = base, 2
    while name in taken:
        name = f"{base}_{i}"
        i += 1
    taken.add(name)
    return name


def _classify(s: ast.stmt) -> str:
    if _is_print(s):
        return "print"
    if isinstance(s, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
        return "big" if _decisions(s) >= 2 else "small"
    return "other"


def _units(body: List[ast.stmt]) -> List[Tuple[int, int, str]]:
    cls = [_classify(s) for s in body]
    units, i = [], 0
    while i < len(body):
        c = cls[i]
        if c == "big":
            units.append((i, i + 1, "block"))
            i += 1
        elif c in ("print", "small"):
            j = i
            while j < len(body) and cls[j] == c:
                j += 1
            if j - i >= 2:
                units.append((i, j, "report" if c == "print" else "checks"))
            i = j
        else:
            i += 1
    return units


def extract_methods(fn: ast.FunctionDef, taken: Set[str]) -> Tuple[List[ast.FunctionDef], List[Dict]]:
    body = fn.body
    doc = body[:1] if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str) else []
    work = body[len(doc):]
    params = [a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs]
    if fn.args.vararg:
        params.append(fn.args.vararg.arg)
    if fn.args.kwarg:
        params.append(fn.args.kwarg.arg)
    helpers: List[ast.FunctionDef] = []
    steps: List[Dict] = []
    replacements: List[Tuple[int, int, List[ast.stmt]]] = []
    for (i, j, kind) in _units(work):
        unit = work[i:j]
        if any(isinstance(n, BAD_IN_UNIT) for s in unit for n in ast.walk(s)):
            continue
        da = set(params) | definite_assigns(work[:i])
        maybe = set(_stores(work[:i])) - da
        loads, stores = _loads(unit), set(_stores(unit))
        if any(n in maybe and n not in stores for n in loads):
            continue
        inputs = [n for n in loads if n in da]
        later = set(_loads(work[j:]))
        outs = [n for n in _stores(unit) if n in later]
        unit_da = definite_assigns(unit)
        bad = False
        for o in outs:
            if o in da:
                if o not in inputs:
                    inputs.append(o)
            elif o not in unit_da:
                bad = True
        if bad:
            continue
        name = _unit_name(kind, unit, outs, taken)
        ret = []
        if outs:
            ret = [ast.Return(value=ast.Name(id=outs[0], ctx=ast.Load()) if len(outs) == 1 else
                              ast.Tuple(elts=[ast.Name(id=o, ctx=ast.Load()) for o in outs], ctx=ast.Load()))]
        desc = {"report": "Print the report lines", "checks": "Run the independent checks"}.get(kind, "Compute " + ", ".join(outs) if outs else "Run one self-contained decision block")
        helper = ast.FunctionDef(
            name=name,
            args=ast.arguments(posonlyargs=[], args=[ast.arg(arg=p) for p in inputs], kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=[ast.Expr(value=ast.Constant(value=f"{desc} (extracted from {fn.name}).")), *copy.deepcopy(unit), *ret],
            decorator_list=[], returns=None,
        )
        if "type_params" in ast.FunctionDef._fields:
            helper.type_params = []
        call = ast.Call(func=ast.Name(id=name, ctx=ast.Load()), args=[ast.Name(id=p, ctx=ast.Load()) for p in inputs], keywords=[])
        if not outs:
            repl = ast.Expr(value=call)
        else:
            tgt = ast.Name(id=outs[0], ctx=ast.Store()) if len(outs) == 1 else ast.Tuple(elts=[ast.Name(id=o, ctx=ast.Store()) for o in outs], ctx=ast.Store())
            repl = ast.Assign(targets=[tgt], value=call)
        replacements.append((i, j, [repl]))
        helpers.append(helper)
        steps.append({"kind": "extract_method", "title": f"Extract `{name}({', '.join(inputs)})`",
                      "detail": f"{desc}. Inputs: {', '.join(inputs) or 'none'}; returns: {', '.join(outs) or 'nothing'}.",
                      "lines": [unit[0].lineno, unit[-1].end_lineno]})
    for i, j, repl in sorted(replacements, key=lambda r: -r[0]):
        work[i:j] = repl
    fn.body = doc + work if (doc + work) else [ast.Pass()]
    return helpers, steps


# ------------------------------------------------------------------- driver
def _eligible(f: FuncInfo, findings: List[Dict]) -> bool:
    if f.is_method or f.enclosing or isinstance(f.node, ast.AsyncFunctionDef):
        return False
    return any(x.get("auto_fix") for x in findings)


def refactor_module(mod: ModuleInfo, per_func_findings: Dict[str, List[Dict]]) -> Optional[Dict]:
    lines = mod.src_lines[:]
    taken: Set[str] = set(mod.global_names)
    edits: List[Tuple[int, int, str]] = []
    all_steps: List[Dict] = []
    changed: List[str] = []
    for f in mod.functions:
        findings = per_func_findings.get(f.name, [])
        if not _eligible(f, findings):
            continue
        fn = copy.deepcopy(f.node)
        steps: List[Dict] = []
        consts, notes = hoist_constants(fn, taken) if any(x["rule"] == "hardcoded_thresholds" for x in findings) else ([], [])
        for c in consts:
            taken.add(c.targets[0].id)
        if consts:
            steps.append({"kind": "constants", "title": "Name the hard-coded thresholds",
                          "detail": ", ".join(f"{c.targets[0].id} = {ast.unparse(c.value)}" for c in consts[:6]) + (" ..." if len(consts) > 6 else ""),
                          "lines": [f.line_start, f.line_end]})
        fn.body, g = guardify(fn.body)
        if g:
            steps.append({"kind": "guard_clause", "title": "Flatten nesting with guard clauses",
                          "detail": f"Turned {g} wrapping `if` into early return(s), removing one nesting level each.", "lines": [f.nesting_line or f.line_start, f.line_end]})
        helpers: List[ast.FunctionDef] = []
        if any(x["rule"] in ("complexity", "elif_chain", "long_function", "io_mixed", "multiple_responsibilities", "duplication", "repeated_branches", "deep_nesting") for x in findings):
            helpers, st = extract_methods(fn, taken)
            steps += st
        if not steps:
            continue
        parts = []
        for c in consts:
            parts.append(ast.unparse(c))
        if consts:
            parts.append("")
        for h in helpers:
            parts.append(ast.unparse(ast.fix_missing_locations(h)))
            parts.append("")
        parts.append(ast.unparse(ast.fix_missing_locations(fn)))
        edits.append((f.line_start, f.line_end, "\n".join(parts).replace("\n\n\n", "\n\n")))
        for s in steps:
            s["function"] = f.name
        all_steps += steps
        changed.append(f.name)
    if not edits:
        return None
    out = lines[:]
    for a, b, text in sorted(edits, key=lambda e: -e[0]):
        out[a - 1:b] = text.split("\n")
    new_src = "\n".join(out) + ("\n" if mod.source.endswith("\n") else "")
    try:
        ast.parse(new_src)
    except SyntaxError as e:  # never ship broken code
        return {"error": f"generated code did not parse: {e}"}
    return {"original": mod.source, "refactored": new_src, "steps": all_steps, "functions": changed}
