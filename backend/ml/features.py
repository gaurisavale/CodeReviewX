"""Feature extraction: one numeric vector per function.

Every feature comes from the deterministic analyzer (structure, detector findings,
factor scores), so the ML layer is trained on exactly what the dashboard shows.
"""
from __future__ import annotations

from typing import Dict, List

from analyzers.quality import run_detectors
from analyzers.structural import analyze_source
from services import scoring

STRUCT_FEATURES = ["lines", "complexity", "cognitive", "nesting", "parameters", "elif_len",
                   "has_docstring", "n_calls", "is_method"]
FACTOR_FEATURES = [f"f_{k}" for k in scoring.FACTOR_KEYS]
COUNT_FEATURES = ["n_critical", "n_warning", "n_info"]
FEATURES: List[str] = STRUCT_FEATURES + FACTOR_FEATURES + COUNT_FEATURES

# plain-language names used when explaining a prediction
PRETTY = {
    "lines": "function length", "complexity": "cyclomatic complexity", "cognitive": "cognitive complexity",
    "nesting": "nesting depth", "parameters": "parameter count", "elif_len": "longest elif chain",
    "has_docstring": "has a docstring", "n_calls": "number of calls", "is_method": "is a method",
    "n_critical": "critical findings", "n_warning": "warning findings", "n_info": "info findings",
}
for _k, _l, *_ in scoring.FACTORS:
    PRETTY[f"f_{_k}"] = f"{_l.lower()} score"


def vector(fn, factors: Dict[str, Dict], findings: List[Dict]) -> Dict[str, float]:
    row = {
        "lines": fn.lines, "complexity": fn.complexity, "cognitive": fn.cognitive, "nesting": fn.nesting,
        "parameters": fn.param_count, "elif_len": fn.elif_len, "has_docstring": int(fn.has_docstring),
        "n_calls": len(fn.calls), "is_method": int(fn.is_method),
        "n_critical": sum(f["severity"] == "critical" for f in findings),
        "n_warning": sum(f["severity"] == "warning" for f in findings),
        "n_info": sum(f["severity"] == "info" for f in findings),
    }
    for k in scoring.FACTOR_KEYS:
        row[f"f_{k}"] = factors[k]["score"]
    return row


def extract_module(code: str) -> List[Dict]:
    """Return [{name, line_start, line_end, features}] for every function in `code`."""
    mod = analyze_source(code)
    det = run_detectors(mod)
    out = []
    for f in mod.functions:
        findings = det[f.name]["findings"]
        factors = scoring.factor_scores(f, findings)
        out.append({"name": f.name, "line_start": f.line_start, "line_end": f.line_end,
                    "features": vector(f, factors, findings)})
    return out
