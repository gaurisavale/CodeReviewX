from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from config import get_settings
from db import get_session
from models import AnalyzeRequest, GithubRequest
from services import ingest, llm
from services.runner import analyze_one, analyze_project, save_file_run
from utils.demo_data import SAMPLES

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/health")
def health():
    cfg = get_settings()
    from ml.model import get_model
    import os
    return {"status": "ok", "version": cfg.version, "environment": cfg.environment,
            "llm": "claude" if os.environ.get("ANTHROPIC_API_KEY") else "fallback", "ml_model": bool(get_model())}


@router.get("/samples")
def samples():
    return {k: {"filename": v[0], "code": v[1]} for k, v in SAMPLES.items()}


@router.get("/demo")
def demo(sample: str = "orders", db: Session = Depends(get_session)):
    filename, code = SAMPLES.get(sample, SAMPLES["orders"])
    out = analyze_one(code, filename)
    out["code"] = code
    return out


@router.post("/analyze")
def analyze_endpoint(req: AnalyzeRequest, db: Session = Depends(get_session)):
    """Analyse one Python file. The structural analyzer produces every number; the interpretation layer only explains them."""
    out = analyze_one(req.code, req.filename or "example.py")
    if req.save:
        out["history_id"] = save_file_run(db, out, req.code, req.project_id).id
    return out


@router.post("/analyze/zip")
async def analyze_zip(file: UploadFile = File(...), project_id: Optional[int] = Form(None), db: Session = Depends(get_session)):
    """Analyse every .py file in an uploaded ZIP archive (nothing is extracted to disk)."""
    data = await file.read()
    try:
        files, notes = ingest.read_zip(data)
    except ingest.IngestError as e:
        raise HTTPException(422, detail={"message": str(e)})
    return analyze_project(db, files, notes, "zip", file.filename or "archive.zip", project_id)


@router.post("/analyze/github")
def analyze_github(req: GithubRequest, db: Session = Depends(get_session)):
    """Shallow-clone a public GitHub repository and analyse its Python files."""
    try:
        files, notes, label = ingest.clone_github(req.url)
    except ingest.IngestError as e:
        raise HTTPException(422, detail={"message": str(e)})
    return analyze_project(db, files, notes, "github", label, req.project_id)
