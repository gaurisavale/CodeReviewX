"""Interpretation layer.

The LLM (or the deterministic fallback) only *explains* facts the analyzer
already produced. It never creates metrics, scores or findings.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Dict, List

MODEL = os.environ.get("CODEREVIEWX_MODEL", "claude-sonnet-4-6")


def _overview(r: Dict) -> Dict:
    fns = r["functions"]
    called = {c for f in fns for c in f["calls"]}
    entry = [f["name"] for f in fns if f["name"] not in called]
    leaves = [f["name"] for f in fns if not f["calls"]]
    io = sorted({x["name"] for f in fns for x in f["responsibilities"]})
    s = r["summary"]
    parts = [f"{s['functions']} function(s) over {s['code_lines']} code lines"]
    if s["imports"]:
        parts.append("imports " + ", ".join(s["imports"][:6]))
    if entry:
        parts.append("entry point(s): " + ", ".join(entry[:5]))
    flows = [f"{f['name']} -> {', '.join(f['calls'][:4])}" for f in fns if f["calls"]][:4]
    if flows:
        parts.append("call flow: " + "; ".join(flows))
    if io:
        parts.append("activities seen: " + ", ".join(io))
    return {"entry_points": entry, "leaf_functions": leaves, "activities": io, "description": ". ".join(x[0].upper() + x[1:] for x in parts) + "."}


def fallback(r: Dict) -> Dict:
    s = r["summary"]
    fs = sorted(r["factors"], key=lambda f: f["score"])
    weak = [f for f in fs if f["score"] < 85][:3]
    crit = [x for x in r["issues"] if x["severity"] == "critical"]
    why = s["verdict"]
    if weak:
        why += " The factors dragging the score down most: " + ", ".join(f"{f['label']} ({f['score']})" for f in weak) + "."
    if crit:
        why += " Critical items: " + "; ".join(f"{x['title']} in {x['function']}" for x in crit[:4]) + "."
    prio = []
    for x in r["issues"][:6]:
        prio.append({"id": x["id"], "title": x["title"], "function": x["function"], "reason": x["why"]})
    rec = ("Bugs and security first (critical items), then error handling and validation, then structure. "
           "The suggested refactor below flattens structure automatically and shows the new score.") if prio else "No findings. Keep functions small and tested."
    ov = _overview(r)
    return {"source": "fallback", "model": None, "summary": s["verdict"], "why": why, "recommendation": rec,
            "priorities": prio, "purpose": ov["description"], "function_purposes": {f["name"]: f["purpose"] for f in r["functions"]}, "overview": ov}


def _claude(r: Dict, key: str) -> Dict:
    facts = {
        "summary": {k: r["summary"][k] for k in ("overall_health", "grade", "functions", "critical", "warning", "info")},
        "factors": {f["key"]: f["score"] for f in r["factors"]},
        "functions": [{"name": f["name"], "health": f["health_score"], "complexity": f["complexity"], "lines": f["lines"],
                       "calls": f["calls"], "params": f["param_names"]} for f in r["functions"]],
        "issues": [{"id": x["id"], "title": x["title"], "function": x["function"], "severity": x["severity"], "metric": f"{x['metric_label']}={x['metric_value']}"} for x in r["issues"][:25]],
    }
    prompt = (
        "You are the interpretation layer of a code review tool. A deterministic analyzer produced the FACTS below. "
        "Explain them for a developer. Do NOT invent metrics, numbers, functions or issues. Reply with JSON only: "
        '{"purpose": "what this code appears to do, 1-2 sentences", "why": "why the health score is what it is, 2-3 sentences", '
        '"recommendation": "ordered plan, 2-3 sentences", "function_purposes": {"<function name>": "one sentence"}}\n\nFACTS:\n' + json.dumps(facts)
    )
    body = json.dumps({"model": MODEL, "max_tokens": 900, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read())
    text = "".join(b.get("text", "") for b in data.get("content", []))
    text = text[text.find("{"): text.rfind("}") + 1]
    j = json.loads(text)
    names = {f["name"] for f in r["functions"]}
    fp = {k: v for k, v in (j.get("function_purposes") or {}).items() if k in names and isinstance(v, str)}
    return {"purpose": str(j.get("purpose", "")), "why": str(j.get("why", "")), "recommendation": str(j.get("recommendation", "")), "function_purposes": fp}


def explain(r: Dict) -> Dict:
    base = fallback(r)
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        base["status_reason"] = "No ANTHROPIC_API_KEY set. Using the deterministic explainer."
        return base
    try:
        c = _claude(r, key)
        for k in ("purpose", "why", "recommendation"):
            if c.get(k):
                base[k] = c[k]
        base["function_purposes"].update(c["function_purposes"])
        base.update({"source": "claude", "model": MODEL, "status_reason": "Claude interpreted the analyzer facts."})
    except (urllib.error.URLError, ValueError, KeyError, TimeoutError, OSError) as e:
        base["status_reason"] = f"Claude call failed ({type(e).__name__}). Using the deterministic explainer."
    return base
