"""Run the full analysis for one file (analyzer + interpretation) and persist it."""
from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from config import get_settings
from db import Analysis
from services import ingest, llm
from services.pipeline import analyze


def analyze_one(code: str, filename: str, explain: bool = True, with_refactor: bool = True) -> Dict:
    cfg = get_settings()
    if not code.strip():
        raise HTTPException(422, detail={"message": "Paste or upload some Python code first.", "line": None})
    if len(code.encode("utf-8")) > cfg.max_code_kb * 1024:
        raise HTTPException(413, detail={"message": f"File is larger than {cfg.max_code_kb} KB.", "line": None})
    try:
        result = analyze(code, filename, with_refactor=with_refactor)
    except SyntaxError as e:
        raise HTTPException(422, detail={"message": f"Syntax error: {e.msg}", "line": e.lineno})
    if explain:
        ex = llm.explain(result)
        result["explanation"] = ex
        for f in result["functions"]:
            f["purpose"] = ex["function_purposes"].get(f["name"], f["purpose"])
        result["engine_status"] = {"structural_analyzer": "ok", "interpretation": ex["source"], "model": ex.get("model"),
                                   "detail": ex.get("status_reason"), "version": cfg.version}
    return result


def save_file_run(db: Session, result: Dict, code: str, project_id: Optional[int] = None, parent_id: Optional[int] = None) -> Analysis:
    s = result["summary"]
    row = Analysis(project_id=project_id, parent_id=parent_id, kind="file", label=result["filename"], overall_health=s["overall_health"],
                   grade=s["grade"], files=1, functions=s["functions"], findings=s["findings_total"], critical=s["critical"],
                   high_risk_functions=s.get("defect_risk_high", 0), max_defect_risk=s.get("defect_risk_max", 0.0), code=code)
    db.add(row)
    db.commit()
    return row


def analyze_project(db: Session, files: List[tuple], notes: List[str], kind: str, label: str, project_id: Optional[int]) -> Dict:
    """Analyse many files, store one parent row plus a row per file, return the project report."""
    results, errors = [], []
    for path, src in files:
        try:
            results.append((analyze(src, path, with_refactor=False), src))
        except SyntaxError as e:
            errors.append({"file": path, "message": f"Syntax error: {e.msg}", "line": e.lineno})
        except Exception as e:  # a parser edge case must not sink the whole run
            errors.append({"file": path, "message": f"Could not analyse: {type(e).__name__}", "line": None})
    if not results:
        raise HTTPException(422, detail={"message": "No file could be analysed.", "errors": errors[:10]})
    agg = ingest.aggregate([r for r, _ in results])
    parent = Analysis(project_id=project_id, kind=kind, label=label, overall_health=agg["overall_health"], grade=agg["grade"],
                      files=agg["files"], functions=agg["functions"], findings=agg["findings"], critical=agg["critical"],
                      high_risk_functions=agg["high_risk_functions"],
                      max_defect_risk=max((f["risk"] for f in agg["riskiest_functions"]), default=0.0),
                      payload=json.dumps({"project": agg, "notes": notes, "errors": errors[:20]}))
    db.add(parent)
    db.commit()
    file_rows = []
    for r, src in results:
        row = save_file_run(db, r, src, project_id, parent.id)
        s = r["summary"]
        file_rows.append({"id": row.id, "filename": r["filename"], "health": s["overall_health"], "grade": s["grade"], "functions": s["functions"],
                          "findings": s["findings_total"], "critical": s["critical"], "high_risk": s.get("defect_risk_high", 0),
                          "max_risk": s.get("defect_risk_max", 0.0)})
    file_rows.sort(key=lambda x: x["health"])
    return {"id": parent.id, "kind": kind, "label": label, "project": agg, "files": file_rows, "notes": notes, "errors": errors[:20]}


def fingerprint(code: str) -> str:
    return hashlib.sha1(code.encode()).hexdigest()[:10]
