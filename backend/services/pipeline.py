"""Glue: structural analysis -> detectors -> scoring -> graph -> refactor."""
from __future__ import annotations

from typing import Dict, List, Optional

from analyzers.quality import run_detectors
from analyzers.structural import ModuleInfo, analyze_source, build_call_graph
from services import scoring
from services.refactor import refactor_module
from ml.features import vector as feature_vector
from ml.model import get_model

SEV_ORDER = {"critical": 0, "warning": 1, "info": 2}


def describe_function(f, resp: Dict[str, List[int]], findings: List[Dict], called_by: List[str]) -> str:
    """Deterministic one-line purpose, derived from structure only."""
    words = [w for w in f.simple_name.strip("_").split("_") if w]
    verb = " ".join(words) if words else f.simple_name
    bits = []
    if f.param_count:
        bits.append(f"takes {f.param_count} input{'s' if f.param_count != 1 else ''}")
    if resp.get("calculation"):
        bits.append("calculates values")
    if f.complexity > 1:
        bits.append(f"makes {f.complexity - 1} decision{'s' if f.complexity != 2 else ''}")
    if resp.get("console I/O"):
        bits.append(f"prints {len(resp['console I/O'])} time{'s' if len(resp['console I/O']) != 1 else ''}")
    if resp.get("persistence / side effects"):
        bits.append("causes side effects (save/send/write)")
    callees = sorted({n for n, _ in f.calls})
    return f"`{verb}`: " + (", ".join(bits) if bits else "small helper") + "."


def _where(x: Dict) -> str:
    ls = x["lines"]
    if len(ls) == 1:
        return f"line {ls[0]}"
    return "lines " + ", ".join(str(n) for n in ls[:5]) + (" ..." if len(ls) > 5 else "")


FACTOR_PRIORITY = {"correctness": 0, "security": 0, "error_handling": 1, "validation": 1}


def analyze(code: str, filename: str = "example.py", with_refactor: bool = True) -> Dict:
    mod: ModuleInfo = analyze_source(code)
    det = run_detectors(mod)
    edges, called_by = build_call_graph(mod)
    funcs: List[Dict] = []
    issues: List[Dict] = []
    risk_model = get_model()
    for f in mod.functions:
        findings = sorted(det[f.name]["findings"], key=lambda x: (SEV_ORDER[x["severity"]], x["line_start"]))
        factors = scoring.factor_scores(f, findings)
        health = scoring.function_health(factors, findings)
        resp = det[f.name]["responsibilities"]
        callees = sorted({t for s, t in edges if s == f.name})
        fd = {
            "name": f.name, "line_start": f.line_start, "line_end": f.line_end, "lines": f.lines,
            "complexity": f.complexity, "cognitive": f.cognitive, "nesting_depth": f.nesting,
            "parameters": f.param_count, "param_names": [p for p in f.params if p not in ("self", "cls")],
            "elif_chain": f.elif_len, "has_docstring": f.has_docstring,
            "health_score": health, "risk": scoring.risk_level(health), "factors": factors,
            "calls": callees, "called_by": sorted(set(called_by[f.name])),
            "responsibilities": [{"name": k, "lines": v[:8]} for k, v in resp.items()],
            "findings": {"critical": sum(x["severity"] == "critical" for x in findings),
                         "warning": sum(x["severity"] == "warning" for x in findings),
                         "info": sum(x["severity"] == "info" for x in findings)},
            "purpose": describe_function(f, resp, findings, called_by[f.name]),
        }
        if risk_model is not None:
            fd["defect_risk"] = risk_model.predict(feature_vector(f, factors, findings))
        weak = sorted(factors.items(), key=lambda kv: kv[1]["score"])[:3]
        weak = [(k, v) for k, v in weak if v["score"] < 100]
        labels = {x[0]: x[1] for x in scoring.FACTORS}
        why = (f"Health {health}/100 ({fd['risk']} risk). " if findings else f"Health {health}/100. No findings: every factor passed its rules. ")
        if weak:
            why += "Weakest factors: " + "; ".join(f"{labels[k]} {v['score']}" for k, v in weak) + ". "
        crit = [x for x in findings if x["severity"] == "critical"]
        if crit:
            why += "Score is capped below 50 because of: " + ", ".join(x["title"] for x in crit) + "."
        fd["explanation"] = {
            "why": why.strip(),
            "evidence": [f"{x['severity'].upper()}: {x['title']} ({x['metric_label']} {x['metric_value']}, {_where(x)})" for x in findings[:12]],
            "recommendation": findings[0]["recommendation"] if findings else "Nothing to fix. Keep it small and tested.",
        }
        funcs.append(fd)
        for x in findings:
            x = dict(x)
            x["id"] = f"I{len(issues) + 1:02d}"
            x["health_score"] = health
            issues.append(x)
    agg = scoring.aggregate(funcs)
    issues.sort(key=lambda x: (SEV_ORDER[x["severity"]], FACTOR_PRIORITY.get(x["factor"], 2), x["health_score"], x["line_start"]))
    for i, x in enumerate(issues, 1):
        x["id"] = f"I{i:02d}"
    fn_ids = {f["name"]: f for f in funcs}
    cnt = {s: sum(1 for x in issues if x["severity"] == s) for s in SEV_ORDER}
    fs = agg["factor_scores"]
    summary = {
        "total_lines": mod.total_lines, "code_lines": mod.code_lines, "blank_lines": mod.blank_lines,
        "comment_lines": mod.comment_lines, "functions": len(funcs), "classes": len(mod.classes),
        "average_function_length": round(sum(f["lines"] for f in funcs) / len(funcs), 1) if funcs else 0,
        "max_function_length": max((f["lines"] for f in funcs), default=0),
        "max_nesting_depth": max((f["nesting_depth"] for f in funcs), default=0),
        "max_complexity": max((f["complexity"] for f in funcs), default=0),
        "avg_complexity": round(sum(f["complexity"] for f in funcs) / len(funcs), 1) if funcs else 0,
        "total_cognitive": sum(f["cognitive"] for f in funcs),
        "overall_health": agg["overall"], "code_health": round(agg["overall"] / 10, 1), "grade": scoring.grade(agg["overall"]),
        "maintainability_score": scoring.maintainability(fs), "risk_score": 100 - agg["overall"],
        "average_health": agg["avg"], "worst_health": agg["worst"],
        "findings_total": len(issues), "critical": cnt["critical"], "warning": cnt["warning"], "info": cnt["info"],
        "imports": sorted(set(mod.imports))[:12],
    }
    if risk_model is not None and funcs:
        summary["defect_risk_high"] = sum(1 for f in funcs if f["defect_risk"]["band"] == "high")
        summary["defect_risk_max"] = max(f["defect_risk"]["probability"] for f in funcs)
        summary["riskiest_function"] = max(funcs, key=lambda f: f["defect_risk"]["probability"])["name"]
    worst = min(funcs, key=lambda f: f["health_score"]) if funcs else None
    summary["worst_function"] = worst["name"] if worst else None
    summary["verdict"] = (
        "No functions found. Add functions to analyze." if not funcs else
        f"Grade {summary['grade']} ({agg['overall']}/100). {cnt['critical']} critical, {cnt['warning']} warning, {cnt['info']} info finding(s) across {len(funcs)} function(s). "
        f"Weakest function: {worst['name']} ({worst['health_score']}/100)."
    )
    factor_meta = [{"key": k, "label": l, "weight": w, "category": c, "description": d, "what": scoring.FACTOR_INFO[k][0], "measures": scoring.FACTOR_INFO[k][1], "how": scoring.FACTOR_INFO[k][2], "score": fs[k],
                    "findings": sum(1 for x in issues if x["factor"] == k)} for (k, l, w, c, d) in scoring.FACTORS]
    result = {
        "filename": filename, "summary": summary, "factors": factor_meta, "categories": agg["categories"],
        "functions": funcs, "issues": issues,
        "graph": {"nodes": [{"id": f["name"], "name": f["name"], "health_score": f["health_score"], "complexity": f["complexity"],
                             "lines": f["lines"], "risk": f["risk"], "issues": sum(f["findings"].values())} for f in funcs],
                  "edges": [{"source": s, "target": t} for s, t in edges]},
        "refactor": None,
        "ml": risk_model.card() if risk_model is not None else None,
    }
    if with_refactor:
        result["refactor"] = build_refactor(mod, det, result)
    return result


def _compact(r: Dict) -> Dict:
    s = r["summary"]
    return {k: s[k] for k in ("overall_health", "grade", "functions", "max_complexity", "max_nesting_depth", "avg_complexity",
                              "max_function_length", "findings_total", "critical", "warning", "info", "maintainability_score")} | {
        "factors": {f["key"]: f["score"] for f in r["factors"]},
        "functions_detail": [{"name": f["name"], "health": f["health_score"], "complexity": f["complexity"], "lines": f["lines"]} for f in r["functions"]]}


def build_refactor(mod: ModuleInfo, det: Dict, before: Dict) -> Optional[Dict]:
    per = {k: v["findings"] for k, v in det.items()}
    r = refactor_module(mod, per)
    if r is None:
        return {"available": False, "reason": "No safe automatic refactor applies. Findings need manual changes (validation, naming, error handling)."}
    if "error" in r:
        return {"available": False, "reason": r["error"]}
    after = analyze(r["refactored"], before["filename"], with_refactor=False)
    manual = sorted({x["title"] for x in after["issues"] if x["rule"] in ("no_validation", "poor_names", "no_exception_handling", "undefined_name", "missing_docstring")})
    return {"available": True, "original": r["original"], "refactored": r["refactored"], "steps": r["steps"],
            "functions": r["functions"], "compiles": True, "before": _compact(before), "after": _compact(after),
            "after_issues": [{"function": x["function"], "title": x["title"], "severity": x["severity"]} for x in after["issues"]][:40],
            "still_manual": manual,
            "note": "Behavior-preserving transformations only (constants, guard clauses, extract method). Naming, validation, error handling and logic bugs still need a human decision."}
