"""SQLAlchemy persistence: projects and analysis history."""
from __future__ import annotations

import datetime as dt
from typing import Iterator, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from config import get_settings


class Base(DeclarativeBase):
    pass


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Analysis(Base):
    """One analysed unit: a pasted file, a file inside a project run, or a whole project run."""
    __tablename__ = "analyses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("analyses.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(12))            # file | zip | github
    label: Mapped[str] = mapped_column(String(300))          # filename, archive name or repo URL
    overall_health: Mapped[int] = mapped_column(Integer)
    grade: Mapped[str] = mapped_column(String(2))
    files: Mapped[int] = mapped_column(Integer, default=1)
    functions: Mapped[int] = mapped_column(Integer, default=0)
    findings: Mapped[int] = mapped_column(Integer, default=0)
    critical: Mapped[int] = mapped_column(Integer, default=0)
    high_risk_functions: Mapped[int] = mapped_column(Integer, default=0)
    max_defect_risk: Mapped[float] = mapped_column(Float, default=0.0)
    code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)       # kept for file rows so they can be re-opened
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)    # JSON summary for zip/github rows
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    project: Mapped[Optional[Project]] = relationship(back_populates="analyses")


_engine = None
_Session = None


def init_db(url: Optional[str] = None) -> None:
    global _engine, _Session
    url = url or get_settings().database_url
    args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    kw = {}
    if url.endswith(":memory:") or url == "sqlite://":
        from sqlalchemy.pool import StaticPool
        kw["poolclass"] = StaticPool
    _engine = create_engine(url, connect_args=args, **kw)
    _Session = sessionmaker(_engine, expire_on_commit=False)
    Base.metadata.create_all(_engine)


def get_session() -> Iterator[Session]:
    if _Session is None:
        init_db()
    with _Session() as s:
        yield s
