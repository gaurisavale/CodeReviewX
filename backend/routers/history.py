import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import Analysis, get_session
from services.runner import analyze_one

router = APIRouter(prefix="/api/history", tags=["history"])


def _row(a: Analysis) -> dict:
    return {"id": a.id, "project_id": a.project_id, "parent_id": a.parent_id, "kind": a.kind, "label": a.label, "overall_health": a.overall_health,
            "grade": a.grade, "files": a.files, "functions": a.functions, "findings": a.findings, "critical": a.critical,
            "high_risk_functions": a.high_risk_functions, "max_defect_risk": a.max_defect_risk, "created_at": a.created_at.isoformat()}


@router.get("")
def list_history(project_id: Optional[int] = None, kind: Optional[str] = None, limit: int = Query(50, le=200), db: Session = Depends(get_session)):
    q = select(Analysis).where(Analysis.parent_id.is_(None)).order_by(Analysis.created_at.desc(), Analysis.id.desc()).limit(limit)
    if project_id is not None:
        q = q.where(Analysis.project_id == project_id)
    if kind:
        q = q.where(Analysis.kind == kind)
    return [_row(a) for a in db.scalars(q)]


@router.get("/{analysis_id}")
def get_run(analysis_id: int, db: Session = Depends(get_session)):
    """Re-open a stored run. File runs are re-analysed from the stored source (deterministic), project runs return their summary."""
    a = db.get(Analysis, analysis_id)
    if a is None:
        raise HTTPException(404, detail={"message": "No such analysis."})
    if a.kind == "file":
        out = analyze_one(a.code or "", a.label)
        out["code"] = a.code
        out["history_id"] = a.id
        return out
    p = json.loads(a.payload or "{}")
    kids = db.scalars(select(Analysis).where(Analysis.parent_id == a.id).order_by(Analysis.overall_health)).all()
    return {**_row(a), **p, "file_runs": [_row(k) for k in kids]}


@router.delete("/{analysis_id}", status_code=204)
def delete_run(analysis_id: int, db: Session = Depends(get_session)):
    a = db.get(Analysis, analysis_id)
    if a is None:
        raise HTTPException(404, detail={"message": "No such analysis."})
    for k in db.scalars(select(Analysis).where(Analysis.parent_id == a.id)):
        db.delete(k)
    db.delete(a)
    db.commit()
