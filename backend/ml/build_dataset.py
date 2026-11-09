"""Build a labelled function-level dataset from git history (SZZ-lite).

For each bug-fix commit (message heuristics), take the PARENT version of every changed
non-test .py file, analyse it, and label a function 1 if a line that the fix deleted or
changed lies inside it, else 0. Features are computed on the pre-fix code, so a model
trained on this predicts "will a later bug fix touch this function?".

usage: python -m ml.build_dataset [--max-commits 500] [--workers 6]
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.features import FEATURES, extract_module  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPOS = os.path.join(HERE, "data", "repos")
OUT = os.path.join(HERE, "data", "dataset.csv")

FIX = re.compile(r"\b(fix(es|ed)?|bug(s|fix)?|crash(es)?|regression|incorrect|wrong|broken|exception|hotfix)\b", re.I)
SKIP = re.compile(r"\b(typo|docs?|documentation|changelog|readme|lint|format(ting)?|style|ci|test(s)?|bump|release|merge|deps?)\b", re.I)
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, errors="replace").stdout


def is_source(path: str) -> bool:
    p = path.lower()
    return p.endswith(".py") and not re.search(r"(^|/)(tests?|docs?|examples?|scripts?|benchmarks?|setup|conftest)(/|\.|$)", p) and "test_" not in p


def old_lines(repo, parent, commit, path):
    """Set of line numbers in the parent file that the commit deleted or changed."""
    lines = set()
    for ln in git(repo, "diff", "-U0", "--no-color", parent, commit, "--", path).splitlines():
        m = HUNK.match(ln)
        if m:
            a, b = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
            lines.update(range(a, a + b) if b else [max(a, 1)])
    return lines


def process_repo(args):
    name, max_commits = args
    repo = os.path.join(REPOS, name)
    rows, n_commits = [], 0
    log = git(repo, "log", "--no-merges", "--format=%H%x09%P%x09%ct%x09%s", "-n", "6000").splitlines()
    for rec in log:
        if n_commits >= max_commits:
            break
        try:
            sha, parents, ts, subj = rec.split("\t", 3)
        except ValueError:
            continue
        parents = parents.split()
        if len(parents) != 1 or not FIX.search(subj) or SKIP.search(subj):
            continue
        files = [f for f in git(repo, "diff", "--name-only", parents[0], sha).splitlines() if is_source(f)]
        if not files or len(files) > 8:
            continue
        n_commits += 1
        for path in files:
            src = git(repo, "show", f"{parents[0]}:{path}")
            if not src or src.count("\n") > 3000:
                continue
            try:
                funcs = extract_module(src)
            except Exception:
                continue
            touched = old_lines(repo, parents[0], sha, path)
            for f in funcs:
                label = int(any(f["line_start"] <= n <= f["line_end"] for n in touched))
                rows.append({"repo": name, "commit": sha[:10], "time": int(ts), "path": path,
                             "function": f["name"], "label": label, **f["features"]})
    return name, n_commits, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-commits", type=int, default=500)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    repos = sorted(d for d in os.listdir(REPOS) if os.path.isdir(os.path.join(REPOS, d, ".git")))
    allrows = []
    with Pool(a.workers) as p:
        for name, nc, rows in p.imap_unordered(process_repo, [(r, a.max_commits) for r in repos]):
            pos = sum(r["label"] for r in rows)
            print(f"{name:10s} commits={nc:4d} functions={len(rows):6d} defective={pos:5d}", flush=True)
            allrows += rows
    cols = ["repo", "commit", "time", "path", "function", "label"] + FEATURES
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(allrows)
    print("total", len(allrows), "defective", sum(r["label"] for r in allrows), "->", OUT)


if __name__ == "__main__":
    main()
