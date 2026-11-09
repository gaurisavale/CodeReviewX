"""Deterministic scoring. Same code in, same numbers out."""
from __future__ import annotations

from typing import Dict, List

PENALTY = {"critical": 50, "warning": 30, "info": 12}

FACTORS = [
    # key, label, weight, category, description
    ("complexity", "Complexity", 14, "complexity", "Independent paths (cyclomatic) and mental load (cognitive)"),
    ("nesting", "Nesting", 8, "complexity", "Depth of nested control flow (elif is not nesting)"),
    ("length", "Length", 8, "maintainability", "Function size in lines"),
    ("parameters", "Parameters", 5, "maintainability", "Signature size"),
    ("naming", "Naming", 8, "readability", "Meaningful identifiers"),
    ("magic_numbers", "Magic numbers", 7, "readability", "Unexplained literals and hard-coded thresholds"),
    ("documentation", "Docs", 3, "readability", "Docstrings"),
    ("duplication", "Duplication", 6, "maintainability", "Repeated logic and branch shapes"),
    ("separation", "Separation", 10, "maintainability", "Single responsibility, I/O kept apart from logic"),
    ("error_handling", "Error handling", 10, "reliability", "Failures caught and reported"),
    ("validation", "Validation", 8, "reliability", "Inputs checked before use"),
    ("correctness", "Correctness", 10, "reliability", "Undefined names, dead code, unused values"),
    ("security", "Security", 8, "security", "Dangerous APIs and secrets"),
]


def _apply_learned_weights() -> None:
    """Optional: replace the hand-set weights with the data-calibrated ones (CODEREVIEWX_USE_LEARNED_WEIGHTS=true)."""
    import json
    import os
    try:
        from config import get_settings
        if not get_settings().use_learned_weights:
            return
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "artifacts", "learned_weights.json")
        learned = json.load(open(path))["weights"]
        FACTORS[:] = [(k, l, learned.get(k, w), c, d) for (k, l, w, c, d) in FACTORS]
    except Exception:
        pass


_apply_learned_weights()
FACTOR_KEYS = [f[0] for f in FACTORS]
WEIGHTS = {f[0]: f[2] for f in FACTORS}
CATEGORY_OF = {f[0]: f[3] for f in FACTORS}
CATEGORIES = ["readability", "maintainability", "complexity", "reliability", "security"]


def _metric_score(key: str, fn) -> int:
    if key == "complexity":
        return int(max(0, min(100, 100 - (fn.complexity - 5) * 4 - max(0, fn.cognitive - 15) * 1)))
    if key == "nesting":
        return int(max(0, min(100, 100 - max(0, fn.nesting - 2) * 25)))
    if key == "length":
        return int(max(0, min(100, 100 - max(0, fn.lines - 20))))
    if key == "parameters":
        return int(max(0, min(100, 100 - max(0, fn.param_count - 3) * 20)))
    return 100


def factor_scores(fn, findings: List[Dict]) -> Dict[str, Dict]:
    out = {}
    for key in FACTOR_KEYS:
        mine = [f for f in findings if f["factor"] == key]
        pen = sum(PENALTY[f["severity"]] for f in mine)
        score = max(0, 100 - pen)
        if key in ("complexity", "nesting", "length", "parameters"):
            score = min(score, _metric_score(key, fn))
        out[key] = {"score": int(score), "findings": len(mine)}
    return out


def function_health(factors: Dict[str, Dict], findings: List[Dict]) -> int:
    tot = sum(WEIGHTS.values())
    h = sum(factors[k]["score"] * WEIGHTS[k] for k in FACTOR_KEYS) / tot
    if any(f["severity"] == "critical" for f in findings):
        h = min(h, 49)
    return int(round(max(0, min(100, h))))


def risk_level(h: int) -> str:
    return "high" if h < 50 else "medium" if h < 75 else "low"


def grade(h: float) -> str:
    return "A" if h >= 85 else "B" if h >= 70 else "C" if h >= 55 else "D" if h >= 40 else "F"


def aggregate(funcs: List[Dict]) -> Dict:
    """funcs: list of function dicts with health_score, lines, factors."""
    if not funcs:
        return {"overall": 100, "factor_scores": {k: 100 for k in FACTOR_KEYS}, "categories": {c: 100 for c in CATEGORIES}, "avg": 100, "worst": 100}
    wts = [max(f["lines"], 5) for f in funcs]
    tw = sum(wts)
    avg = sum(f["health_score"] * w for f, w in zip(funcs, wts)) / tw
    worst = min(f["health_score"] for f in funcs)
    overall = int(round(0.6 * avg + 0.4 * worst))
    fs = {k: int(round(sum(f["factors"][k]["score"] * w for f, w in zip(funcs, wts)) / tw)) for k in FACTOR_KEYS}
    cats = {}
    for c in CATEGORIES:
        ks = [k for k in FACTOR_KEYS if CATEGORY_OF[k] == c]
        cats[c] = int(round(sum(fs[k] * WEIGHTS[k] for k in ks) / sum(WEIGHTS[k] for k in ks)))
    return {"overall": overall, "factor_scores": fs, "categories": cats, "avg": round(avg, 1), "worst": worst}


def maintainability(fs: Dict[str, int]) -> int:
    ks = ["complexity", "nesting", "length", "duplication", "separation", "naming", "documentation"]
    return int(round(sum(fs[k] for k in ks) / len(ks)))


# Plain-language help shown in hover tooltips: what it is, what is measured, how the score is computed.
FACTOR_INFO = {
    "complexity": ("How many different paths the code can take. More paths means more tests and more places for bugs.",
                   "Cyclomatic = 1 + every if/elif, for, while, except, and/or, ternary and comprehension. Cognitive adds extra weight for nesting.",
                   "Score = 100 - 4 x (cyclomatic - 5) - (cognitive over 15), then capped by finding penalties. Warning at cyclomatic 10+, critical at 20+. An if/elif chain of 4+ branches is a warning."),
    "nesting": ("How deeply if/for/while/try blocks sit inside each other. Deep nesting hides the main logic.",
                "Max depth of nested control blocks. An elif is NOT counted as extra depth.",
                "Score = 100 - 25 x (depth - 2). Finding: info at depth 3, warning at 4, critical at 5+."),
    "length": ("How long the function is. Long functions usually do several jobs.",
               "Lines from the def line to the last line of the function.",
               "Score = 100 - (lines - 20). Finding: info at 30+ lines, warning at 50+, critical at 100+."),
    "parameters": ("How many inputs the function takes. Many inputs are hard to remember and usually mean too many jobs.",
                   "Count of parameters (self and cls are ignored).",
                   "Score = 100 - 20 x (count - 3). Finding: warning at 5+, critical at 8+."),
    "naming": ("Whether variable and parameter names say what they mean.",
               "Counts names of 1-2 letters (a, w, t, f) or vague words (tmp, data, val, obj). Loop counters like i, j, k are allowed.",
               "Each finding subtracts a penalty: info 12, or warning 30 when 3+ unclear names. Score = 100 - penalties."),
    "magic_numbers": ("Raw numbers in the code whose meaning is not explained, such as 18.5 or 5000.",
                      "Numeric literals other than 0, 1, 2, -1, 100. Split into thresholds (inside comparisons) and magic numbers (in calculations). Defaults, UPPER_CASE constants, indexes and round() digits are ignored.",
                      "Each group subtracts info 12, or warning 30 when 3+ literals. Score = 100 - penalties."),
    "documentation": ("Whether the function explains itself with a docstring.",
                      "Functions of 8+ lines (not starting with _) that have no docstring.",
                      "Missing docstring is an info finding: 12 points off, so 88."),
    "duplication": ("Copy-pasted logic. Copies drift apart and bugs get fixed in only one place.",
                    "Statement blocks of 14+ AST nodes with the same structure (names and constants ignored), plus if/elif chains where 3+ branches have identical shape.",
                    "Warning (30 off) for repeated blocks or 4+ same-shape branches, info (12 off) for 3."),
    "separation": ("Whether one function does one job. Logic should not be tangled with printing or saving.",
                   "Detects print()/input() mixed with calculations or decisions, and counts distinct responsibilities: console I/O, calculation, validation, persistence, decision logic, formatting.",
                   "Each finding is a warning (30 off). Mixed I/O: warning at 2+ prints. Multiple responsibilities: 3+ kinds in a function of 12+ lines."),
    "error_handling": ("Whether failures are caught and reported instead of crashing or being hidden.",
                       "Finds risky operations (open, int(), float(), division by a variable, save/send/connect style calls, dict-key access on inputs) with no try/except, and bare or silent except blocks.",
                       "Each finding is a warning: 30 off, so a function with one such finding scores 70."),
    "validation": ("Whether inputs are checked before being used.",
                   "Looks for raise, assert, isinstance() or an early guard on the parameters in functions of 6+ lines. None found means unvalidated.",
                   "Warning (30 off) with 2+ parameters, info (12 off) with 1. Private helpers starting with _ are skipped."),
    "correctness": ("Likely bugs and dead code.",
                    "Undefined names (read but never defined), mutable default arguments, unreachable code, unused parameters or variables, == None.",
                    "Undefined name is critical (50 off). Unreachable code and mutable defaults are warnings (30 off). The rest are info (12 off)."),
    "security": ("Dangerous patterns that attackers can exploit.",
                 "eval/exec, os.system or shell=True, SQL built from f-strings or concatenation, pickle/yaml.load, verify=False, hard-coded passwords or keys.",
                 "SQL injection, eval/exec and shell execution are critical (50 off). Others are warnings (30 off)."),
}
