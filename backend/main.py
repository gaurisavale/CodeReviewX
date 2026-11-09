"""CodeReviewX API. The structural analyzer is the source of truth; the ML model ranks risk; the LLM only explains."""
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from db import init_db
from routers import analysis, history, model, projects

cfg = get_settings()
logging.basicConfig(level=cfg.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("codereviewx")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from ml.model import get_model
    m = get_model()
    log.info("CodeReviewX %s started (db=%s, ml_model=%s)", cfg.version, cfg.database_url.split("///")[0], "loaded" if m else "missing")
    yield


app = FastAPI(
    title=cfg.app_name, version=cfg.version, lifespan=lifespan,
    description="Explainable code-health reviewer. Deterministic AST analysis measures, a trained model ranks defect risk, an LLM (optional) explains.",
    openapi_tags=[{"name": "analysis", "description": "Analyse code"}, {"name": "history", "description": "Stored runs"},
                  {"name": "projects", "description": "Group runs and track trends"}, {"name": "model", "description": "Defect-risk model card"}],
)
app.add_middleware(CORSMiddleware, allow_origins=cfg.cors_origins, allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Request-ID", "X-Process-Time"])


@app.middleware("http")
async def timing(request: Request, call_next):
    rid = uuid.uuid4().hex[:8]
    t = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - t) * 1000
    response.headers["X-Request-ID"] = rid
    response.headers["X-Process-Time"] = f"{ms:.0f}ms"
    log.info("%s %s %s %.0fms rid=%s", request.method, request.url.path, response.status_code, ms, rid)
    return response


for r in (analysis.router, history.router, projects.router, model.router):
    app.include_router(r)
