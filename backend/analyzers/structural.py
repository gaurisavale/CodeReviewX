"""Structural analyzer (v2).

Pure `ast` based. This module is the SOURCE OF TRUTH for every number the
product shows. Nothing here uses an LLM.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple

SCOPE_BREAK = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
FUNC_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef)
COMPOUND = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith)


def walk_scope(node: ast.AST) -> Iterator[ast.AST]:
    """Walk a function/module body without entering nested defs/classes."""
    stack = list(ast.iter_child_nodes(node))
    while stack:
        n = stack.pop()
        yield n
        if isinstance(n, SCOPE_BREAK):
            continue
        stack.extend(ast.iter_child_nodes(n))


def set_parents(tree: ast.AST) -> None:
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n):
            c._parent = n  # type: ignore[attr-defined]


def ancestors(n: ast.AST) -> Iterator[ast.AST]:
    while hasattr(n, "_parent"):
        n = n._parent  # type: ignore[attr-defined]
        yield n


@dataclass
class FuncInfo:
    name: str
    simple_name: str
    node: ast.AST
    line_start: int
    line_end: int
    lines: int
    params: List[str]
    param_count: int
    complexity: int
    cognitive: int
    nesting: int
    nesting_line: int
    elif_len: int
    elif_start: int
    elif_end: int
    calls: List[Tuple[str, int]]
    has_docstring: bool
    class_name: Optional[str]
    enclosing: List[ast.AST] = field(default_factory=list)

    @property
    def is_method(self) -> bool:
        return self.class_name is not None


@dataclass
class ModuleInfo:
    tree: ast.Module
    source: str
    src_lines: List[str]
    total_lines: int
    blank_lines: int
    comment_lines: int
    code_lines: int
    functions: List[FuncInfo]
    classes: List[str]
    global_names: set
    imports: List[str]


# ---------------------------------------------------------------- complexity
def cyclomatic(fn: ast.AST) -> int:
    c = 1
    for n in walk_scope(fn):
        if isinstance(n, (ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.Assert)):
            c += 1
        elif isinstance(n, ast.BoolOp):
            c += len(n.values) - 1
        elif isinstance(n, ast.comprehension):
            c += 1 + len(n.ifs)
        elif hasattr(ast, "match_case") and isinstance(n, ast.match_case):
            c += 1
    return c


def _expr_cog(node: ast.AST, nesting: int) -> int:
    total = 0
    stack = [node]
    while stack:
        n = stack.pop()
        if isinstance(n, ast.BoolOp):
            total += 1
        elif isinstance(n, ast.IfExp):
            total += 1 + nesting
        if isinstance(n, SCOPE_BREAK):
            continue
        stack.extend(ast.iter_child_nodes(n))
    return total


def _cog_body(body: List[ast.stmt], nesting: int) -> int:
    t = 0
    for st in body:
        t += _cog_stmt(st, nesting)
    return t


def _cog_if(st: ast.If, nesting: int, elif_: bool) -> int:
    t = 1 + (0 if elif_ else nesting)
    t += _expr_cog(st.test, nesting)
    t += _cog_body(st.body, nesting + 1)
    if len(st.orelse) == 1 and isinstance(st.orelse[0], ast.If):
        t += _cog_if(st.orelse[0], nesting, True)
    elif st.orelse:
        t += 1 + _cog_body(st.orelse, nesting + 1)
    return t


def _cog_stmt(st: ast.stmt, nesting: int) -> int:
    if isinstance(st, ast.If):
        return _cog_if(st, nesting, False)
    if isinstance(st, (ast.For, ast.AsyncFor, ast.While)):
        head = st.iter if hasattr(st, "iter") else st.test  # type: ignore[attr-defined]
        return 1 + nesting + _expr_cog(head, nesting) + _cog_body(st.body, nesting + 1) + _cog_body(st.orelse, nesting + 1)
    if isinstance(st, ast.Try):
        t = _cog_body(st.body, nesting)
        for h in st.handlers:
            t += 1 + nesting + _cog_body(h.body, nesting + 1)
        return t + _cog_body(st.orelse, nesting) + _cog_body(st.finalbody, nesting)
    if isinstance(st, (ast.With, ast.AsyncWith)):
        return _cog_body(st.body, nesting)
    if isinstance(st, SCOPE_BREAK):
        return 0
    return _expr_cog(st, nesting)


def nesting_info(body: List[ast.stmt], depth: int = 0) -> Tuple[int, int]:
    """Max control-flow nesting. An elif is NOT extra nesting."""
    best, best_line = depth, 0
    for st in body:
        if isinstance(st, ast.If):
            cur: Optional[ast.If] = st
            d = depth + 1
            if d > best:
                best, best_line = d, st.lineno
            while cur is not None:
                b, bl = nesting_info(cur.body, d)
                if b > best:
                    best, best_line = b, bl
                if len(cur.orelse) == 1 and isinstance(cur.orelse[0], ast.If):
                    cur = cur.orelse[0]
                else:
                    if cur.orelse:
                        b, bl = nesting_info(cur.orelse, d)
                        if b > best:
                            best, best_line = b, bl
                    cur = None
        elif isinstance(st, COMPOUND):
            d = depth + 1
            if d > best:
                best, best_line = d, st.lineno
            parts: List[List[ast.stmt]] = [st.body]
            if isinstance(st, ast.Try):
                parts += [h.body for h in st.handlers] + [st.orelse, st.finalbody]
            elif hasattr(st, "orelse"):
                parts.append(st.orelse)  # type: ignore[attr-defined]
            for p in parts:
                b, bl = nesting_info(p, d)
                if b > best:
                    best, best_line = b, bl
    return best, best_line


def longest_elif_chain(body_owner: ast.AST) -> Tuple[int, int, int]:
    best = (0, 0, 0)
    for n in walk_scope(body_owner):
        if isinstance(n, ast.If) and not _is_elif(n):
            length, cur, last = 1, n, n
            while len(cur.orelse) == 1 and isinstance(cur.orelse[0], ast.If):
                cur = cur.orelse[0]
                length += 1
                last = cur
            end = (cur.orelse[-1].end_lineno if cur.orelse else cur.body[-1].end_lineno) or n.lineno
            if length > best[0]:
                best = (length, n.lineno, end)
    return best


def _is_elif(n: ast.If) -> bool:
    p = getattr(n, "_parent", None)
    return isinstance(p, ast.If) and len(p.orelse) == 1 and p.orelse[0] is n


# ------------------------------------------------------------------- helpers
def param_names(fn: ast.AST) -> List[str]:
    a = fn.args  # type: ignore[attr-defined]
    names = [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs]
    if a.vararg:
        names.append(a.vararg.arg)
    if a.kwarg:
        names.append(a.kwarg.arg)
    return names


def call_name(c: ast.Call) -> Optional[str]:
    f = c.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def dotted(node: ast.AST) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def stored_names(scope: ast.AST) -> set:
    out = set()
    for n in walk_scope(scope):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            out.add(n.id)
        elif isinstance(n, SCOPE_BREAK):
            out.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                out.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        elif isinstance(n, ast.arg):  # lambda args
            out.add(n.arg)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            out.update(n.names)
    return out


def _count_lines(src: str):
    lines = src.splitlines()
    blank = sum(1 for l in lines if not l.strip())
    comment = sum(1 for l in lines if l.strip().startswith("#"))
    return lines, len(lines), blank, comment


def analyze_source(code: str) -> ModuleInfo:
    tree = ast.parse(code)
    set_parents(tree)
    lines, total, blank, comment = _count_lines(code)
    classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    imports = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imports += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            imports.append(n.module or "")
    funcs: List[FuncInfo] = []
    seen: Dict[str, int] = {}
    for n in ast.walk(tree):
        if not isinstance(n, FUNC_TYPES):
            continue
        cls = None
        enclosing: List[ast.AST] = []
        for a in ancestors(n):
            if isinstance(a, ast.ClassDef) and cls is None and not enclosing:
                cls = a.name
            if isinstance(a, FUNC_TYPES):
                enclosing.append(a)
        qual = f"{cls}.{n.name}" if cls else n.name
        if qual in seen:
            seen[qual] += 1
            qual = f"{qual}_L{n.lineno}"
        else:
            seen[qual] = 1
        start = min([n.lineno] + [d.lineno for d in n.decorator_list])
        end = n.end_lineno or n.lineno
        params = param_names(n)
        eff = [p for p in params if p not in ("self", "cls")]
        nest, nest_line = nesting_info(n.body)
        el, es, ee = longest_elif_chain(n)
        calls = []
        for c in walk_scope(n):
            if isinstance(c, ast.Call):
                nm = call_name(c)
                if nm:
                    calls.append((nm, c.lineno))
        funcs.append(FuncInfo(
            name=qual, simple_name=n.name, node=n, line_start=start, line_end=end,
            lines=end - start + 1, params=params, param_count=len(eff),
            complexity=cyclomatic(n), cognitive=_cog_body(n.body, 0),
            nesting=nest, nesting_line=nest_line, elif_len=el, elif_start=es, elif_end=ee,
            calls=sorted(calls, key=lambda x: x[1]), has_docstring=ast.get_docstring(n) is not None,
            class_name=cls, enclosing=enclosing,
        ))
    funcs.sort(key=lambda f: f.line_start)
    return ModuleInfo(
        tree=tree, source=code, src_lines=lines, total_lines=total, blank_lines=blank,
        comment_lines=comment, code_lines=total - blank - comment, functions=funcs,
        classes=classes, global_names=stored_names(tree), imports=imports,
    )


def build_call_graph(mod: ModuleInfo) -> Tuple[List[Tuple[str, str]], Dict[str, List[str]]]:
    by_simple: Dict[str, List[str]] = {}
    for f in mod.functions:
        by_simple.setdefault(f.simple_name, []).append(f.name)
    edges, called_by = [], {f.name: [] for f in mod.functions}
    for f in mod.functions:
        done = set()
        for nm, _ in f.calls:
            for target in by_simple.get(nm, []):
                if target != f.name and (f.name, target) not in done:
                    done.add((f.name, target))
                    edges.append((f.name, target))
                    called_by[target].append(f.name)
    return edges, called_by
