from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db import Analysis, Project, get_session
from models import ProjectCreate

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _proj(p: Project, db: Session) -> dict:
    runs = db.scalars(select(Analysis).where(Analysis.project_id == p.id, Analysis.parent_id.is_(None)).order_by(Analysis.created_at)).all()
    last = runs[-1] if runs else None
    return {"id": p.id, "name": p.name, "description": p.description, "created_at": p.created_at.isoformat(), "runs": len(runs),
            "latest_health": last.overall_health if last else None, "latest_grade": last.grade if last else None,
            "trend": [{"at": r.created_at.isoformat(), "health": r.overall_health, "label": r.label} for r in runs[-20:]]}


@router.get("")
def list_projects(db: Session = Depends(get_session)):
    return [_proj(p, db) for p in db.scalars(select(Project).order_by(Project.created_at.desc()))]


@router.post("", status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_session)):
    p = Project(name=body.name.strip(), description=body.description)
    db.add(p)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, detail={"message": "A project with that name already exists."})
    return _proj(p, db)


@router.get("/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_session)):
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(404, detail={"message": "No such project."})
    return _proj(p, db)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_session)):
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(404, detail={"message": "No such project."})
    db.delete(p)
    db.commit()
