"""Multi-file ingestion: ZIP archives and public GitHub repositories."""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from typing import Dict, List, Tuple

from config import get_settings

SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "env", "site-packages", "__pycache__", "build", "dist", ".tox", ".mypy_cache", "migrations"}
GITHUB_RE = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?(\.git)?/?$")


class IngestError(ValueError):
    pass


TEST_DIRS = {"tests", "test", "testing"}


def _keep(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    skip = SKIP_DIRS if get_settings().include_tests else SKIP_DIRS | TEST_DIRS
    name = parts[-1]
    if not get_settings().include_tests and (name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py"):
        return False
    return path.endswith(".py") and not any(p in skip or p.startswith(".") for p in parts[:-1])


def read_zip(data: bytes) -> Tuple[List[Tuple[str, str]], List[str]]:
    """Return ([(path, source)], [skipped notes]). Nothing is extracted to disk."""
    cfg = get_settings()
    if len(data) > cfg.max_zip_mb * 1024 * 1024:
        raise IngestError(f"Archive is larger than {cfg.max_zip_mb} MB.")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise IngestError("That file is not a valid ZIP archive.")
    infos = [i for i in zf.infolist() if not i.is_dir()]
    if sum(i.file_size for i in infos) > cfg.max_unzipped_mb * 1024 * 1024:
        raise IngestError(f"Archive expands to more than {cfg.max_unzipped_mb} MB.")
    return _collect(((i.filename, i.file_size, lambda i=i: zf.read(i)) for i in infos if _keep(i.filename) and ".." not in i.filename.split("/")))


def _collect(items) -> Tuple[List[Tuple[str, str]], List[str]]:
    cfg = get_settings()
    out, notes = [], []
    items = sorted(items, key=lambda t: t[1], reverse=True)
    for path, size, reader in items:
        if len(out) >= cfg.max_files:
            notes.append(f"Stopped at {cfg.max_files} files; the rest were not analysed.")
            break
        if size > cfg.max_file_kb * 1024:
            notes.append(f"Skipped {path} (over {cfg.max_file_kb} KB).")
            continue
        try:
            out.append((path, reader().decode("utf-8")))
        except UnicodeDecodeError:
            notes.append(f"Skipped {path} (not UTF-8).")
    if not out:
        raise IngestError("No Python files found.")
    return out, sorted(set(notes))


def clone_github(url: str) -> Tuple[List[Tuple[str, str]], List[str], str]:
    """Shallow-clone a public GitHub repo into a temp dir, read its .py files, delete it."""
    cfg = get_settings()
    url = url.strip()
    if not GITHUB_RE.match(url):
        raise IngestError("Only public https://github.com/<owner>/<repo> URLs are accepted.")
    tmp = tempfile.mkdtemp(prefix="crx_")
    try:
        try:
            subprocess.run(["git", "clone", "--depth", "1", "--quiet", url, tmp + "/repo"], check=True, capture_output=True,
                           timeout=cfg.git_timeout_s, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        except subprocess.TimeoutExpired:
            raise IngestError("Cloning took too long.")
        except subprocess.CalledProcessError:
            raise IngestError("Could not clone that repository (is it public?).")
        root = tmp + "/repo"
        items = []
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in SKIP_DIRS and not d.startswith(".")]
            for f in fn:
                full = os.path.join(dp, f)
                rel = os.path.relpath(full, root)
                if _keep(rel):
                    items.append((rel, os.path.getsize(full), lambda p=full: open(p, "rb").read()))
        files, notes = _collect(items)
        return files, notes, url.rstrip("/").removesuffix(".git").split("github.com/")[-1]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def aggregate(results: List[Dict]) -> Dict:
    """Project-level summary from per-file analysis results."""
    ok = [r for r in results if "summary" in r]
    if not ok:
        return {"overall_health": 0, "grade": "F", "files": 0, "functions": 0}
    from services.scoring import grade
    wt = [max(r["summary"]["code_lines"], 5) for r in ok]
    health = round(sum(w * r["summary"]["overall_health"] for w, r in zip(wt, ok)) / sum(wt))
    fs: Dict[str, float] = {}
    for r in ok:
        for f in r["factors"]:
            fs[f["key"]] = fs.get(f["key"], 0) + f["score"] * max(r["summary"]["code_lines"], 5)
    fs = {k: round(v / sum(wt)) for k, v in fs.items()}
    funcs = [dict(name=f["name"], file=r["filename"], health=f["health_score"], line=f["line_start"],
                  risk=f.get("defect_risk", {}).get("probability", 0.0), band=f.get("defect_risk", {}).get("band", "low"))
             for r in ok for f in r["functions"]]
    return {
        "overall_health": health, "grade": grade(health), "files": len(ok),
        "functions": sum(r["summary"]["functions"] for r in ok), "code_lines": sum(r["summary"]["code_lines"] for r in ok),
        "findings": sum(r["summary"]["findings_total"] for r in ok), "critical": sum(r["summary"]["critical"] for r in ok),
        "warning": sum(r["summary"]["warning"] for r in ok), "info": sum(r["summary"]["info"] for r in ok),
        "high_risk_functions": sum(f["band"] == "high" for f in funcs), "factor_scores": fs,
        "riskiest_functions": sorted(funcs, key=lambda f: -f["risk"])[:10],
        "worst_files": sorted(({"file": r["filename"], "health": r["summary"]["overall_health"], "grade": r["summary"]["grade"]} for r in ok), key=lambda x: x["health"])[:10],
    }
