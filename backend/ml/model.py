"""Runtime wrapper around the trained defect-risk model.

The model is a standardised logistic regression, so every prediction decomposes exactly
into per-feature contributions (coefficient x standardised value). Related features
(e.g. `nesting` and its factor score `f_nesting`) are summed into one driver so the
explanation reads in the same vocabulary as the rest of the dashboard.
"""
from __future__ import annotations

import json
import math
import os
from typing import Dict, List, Optional

import joblib

from ml.features import FEATURES, PRETTY

ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")

GROUPS = {
    "lines": "length", "f_length": "length",
    "complexity": "complexity", "cognitive": "complexity", "f_complexity": "complexity", "elif_len": "complexity",
    "nesting": "nesting", "f_nesting": "nesting",
    "parameters": "parameters", "f_parameters": "parameters",
    "has_docstring": "documentation", "f_documentation": "documentation",
    "n_calls": "number of calls", "is_method": "is a method",
    "n_critical": "detector findings", "n_warning": "detector findings", "n_info": "detector findings",
}


class RiskModel:
    def __init__(self, path: Optional[str] = None):
        path = path or os.path.join(ART, "risk_model.joblib")
        bundle = joblib.load(path)
        self.pipe = bundle["model"]
        self.features: List[str] = bundle["features"]
        self.scaler = self.pipe.named_steps["standardscaler"]
        self.clf = self.pipe.named_steps["logisticregression"]
        with open(os.path.join(os.path.dirname(path), "metrics.json")) as fh:
            self.meta = json.load(fh)
        self.thr_high = self.meta["thresholds"]["high"]
        self.thr_med = self.meta["thresholds"]["medium"]

    def band(self, p: float) -> str:
        return "high" if p >= self.thr_high else "medium" if p >= self.thr_med else "low"

    def predict(self, feats: Dict[str, float]) -> Dict:
        xs = [(float(feats[k]) - m) / s for k, m, s in zip(self.features, self.scaler.mean_, self.scaler.scale_)]
        contrib = [c * x for c, x in zip(self.clf.coef_[0], xs)]
        z = float(self.clf.intercept_[0] + sum(contrib))
        p = 1.0 / (1.0 + math.exp(-z))
        drivers: Dict[str, float] = {}
        for k, c in zip(self.features, contrib):
            name = GROUPS.get(k, PRETTY.get(k, k).replace(" score", ""))
            if k == "is_method" and not feats[k]:
                name = "stand-alone function (not a method)"
            drivers[name] = drivers.get(name, 0.0) + float(c)
        top = sorted(drivers.items(), key=lambda kv: -abs(kv[1]))[:4]
        return {"probability": round(p, 4), "band": self.band(p),
                "drivers": [{"name": n, "effect": round(float(v), 3), "direction": "raises" if v > 0 else "lowers"} for n, v in top if abs(v) >= 0.03]}

    def card(self) -> Dict:
        best = self.meta["models"][self.meta["production_model"]]
        base = self.meta["models"]["Lines only"]
        return {
            "name": self.meta["production_model"], "trained_at": self.meta["trained_at"], "protocol": self.meta["protocol"],
            "functions": self.meta["n_functions"], "defective": self.meta["n_defective"], "repos": len(self.meta["repos"]),
            "auc": round(best["auc_mean"], 3), "auc_std": round(best["auc_std"], 3), "recall_at_20": round(best["r20_mean"], 3),
            "baseline_lines_auc": round(base["auc_mean"], 3),
            "thresholds": self.meta["thresholds"],
        }


_model: Optional[RiskModel] = None
_tried = False


def get_model() -> Optional[RiskModel]:
    """Lazy singleton; returns None if the artifacts are missing (the app still works)."""
    global _model, _tried
    if not _tried:
        _tried = True
        try:
            _model = RiskModel()
        except Exception:
            _model = None
    return _model
