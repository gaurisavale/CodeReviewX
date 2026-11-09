"""Train and evaluate the defect-risk model.

Evaluation protocol: leave-one-repository-out (LORO). Each repo is held out in turn, the
model is fit on the other repos, and scored on the held-out one, so no project leaks
into its own test set. Reported: ROC-AUC, average precision, precision@top-20%, and
recall@top-20% (the review-effort view: "if you read the riskiest 20%, what do you catch?").

usage: python -m ml.train
"""
from __future__ import annotations

import json
import os
import sys
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score, roc_curve
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.features import FACTOR_FEATURES, FEATURES  # noqa: E402
from services import scoring  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "dataset.csv")
ART = os.path.join(HERE, "artifacts")
SEED = 7


def lr():
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=2000, random_state=SEED))


def gb():
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.06, max_iter=150, l2_regularization=1.0, random_state=SEED)


class HandScore:
    """Baseline: risk = 100 - the rule-based health score (no learning)."""
    def fit(self, X, y):
        return self

    def predict_proba(self, X):
        w = np.array([scoring.WEIGHTS[k[2:]] for k in FACTOR_FEATURES], dtype=float)
        h = (X[FACTOR_FEATURES].values * w).sum(1) / w.sum()
        h = np.where(X["n_critical"].values > 0, np.minimum(h, 49), h)
        r = (100 - h) / 100
        return np.c_[1 - r, r]


MODELS = {
    "Base rate (no model)": (lambda: DummyClassifier(strategy="prior"), FEATURES),
    "Lines only": (lr, ["lines"]),
    "Cyclomatic complexity only": (lr, ["complexity"]),
    "Rule-based health score (no learning)": (lambda: HandScore(), FEATURES),
    "Logistic regression (13 factor scores)": (lr, FACTOR_FEATURES),
    "Logistic regression (all features)": (lr, FEATURES),
    "Gradient boosting (all features)": (gb, FEATURES),
}


def topk(y, p, frac=0.2):
    k = max(1, int(round(len(y) * frac)))
    idx = np.argsort(-p)[:k]
    return float(y[idx].mean()), float(y[idx].sum() / max(1, y.sum()))


def main():
    df = pd.read_csv(DATA)
    df = df.drop_duplicates(subset=["repo", "path", "function", "commit"]).reset_index(drop=True)
    y = df["label"].values
    repos = sorted(df["repo"].unique())
    print(f"{len(df)} functions, {y.sum()} defective ({y.mean():.1%}), {len(repos)} repos")

    results, oof = {}, {}
    for name, (mk, cols) in MODELS.items():
        per, p_all = [], np.zeros(len(df))
        for r in repos:
            te = (df["repo"] == r).values
            m = mk()
            m.fit(df.loc[~te, cols], y[~te])
            p = m.predict_proba(df.loc[te, cols])[:, 1]
            p_all[te] = p
            if len(set(y[te])) > 1:
                pr, rc = topk(y[te], p)
                per.append({"repo": r, "n": int(te.sum()), "pos": int(y[te].sum()), "auc": roc_auc_score(y[te], p),
                            "ap": average_precision_score(y[te], p), "p@20": pr, "r@20": rc})
        pr, rc = topk(y, p_all)
        results[name] = {
            "auc_mean": float(np.mean([x["auc"] for x in per])), "auc_std": float(np.std([x["auc"] for x in per])),
            "ap_mean": float(np.mean([x["ap"] for x in per])),
            "p20_mean": float(np.mean([x["p@20"] for x in per])), "r20_mean": float(np.mean([x["r@20"] for x in per])),
            "pooled_auc": float(roc_auc_score(y, p_all)), "per_repo": per,
        }
        oof[name] = p_all
        print(f"{name:42s} AUC {results[name]['auc_mean']:.3f} +/- {results[name]['auc_std']:.3f}  AP {results[name]['ap_mean']:.3f}  "
              f"P@20 {results[name]['p20_mean']:.3f}  R@20 {results[name]['r20_mean']:.3f}")

    # ---- production model: logistic regression on all features (explainable), fit on every repo
    final = lr()
    final.fit(df[FEATURES], y)
    p_train = final.predict_proba(df[FEATURES])[:, 1]
    thr_high, thr_med = float(np.quantile(p_train, 0.90)), float(np.quantile(p_train, 0.70))
    scaler, clf = final.named_steps["standardscaler"], final.named_steps["logisticregression"]
    coefs = dict(zip(FEATURES, clf.coef_[0].tolist()))

    # ---- calibrated factor weights: LR on the 13 factor scores only (lower score -> more risk)
    wm = lr()
    wm.fit(df[FACTOR_FEATURES], y)
    raw = -wm.named_steps["logisticregression"].coef_[0]
    raw = np.clip(raw, 0, None)
    learned = {}
    if raw.sum() > 0:
        scaled = raw / raw.sum() * sum(scoring.WEIGHTS.values())
        learned = {k[2:]: round(float(max(1.0, v)), 1) for k, v in zip(FACTOR_FEATURES, scaled)}

    os.makedirs(ART, exist_ok=True)
    joblib.dump({"model": final, "features": FEATURES}, os.path.join(ART, "risk_model.joblib"))
    meta = {
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"), "n_functions": int(len(df)), "n_defective": int(y.sum()),
        "base_rate": float(y.mean()), "repos": {r: {"functions": int((df.repo == r).sum()), "defective": int(y[(df.repo == r).values].sum())} for r in repos},
        "protocol": "leave-one-repository-out", "models": results, "production_model": "Logistic regression (all features)",
        "coefficients": coefs, "thresholds": {"high": thr_high, "medium": thr_med},
        "feature_means": dict(zip(FEATURES, scaler.mean_.tolist())), "feature_scales": dict(zip(FEATURES, scaler.scale_.tolist())),
        "hand_weights": scoring.WEIGHTS, "learned_weights": learned,
    }
    json.dump(meta, open(os.path.join(ART, "metrics.json"), "w"), indent=2)
    json.dump({"weights": learned, "source": "logistic regression on 13 factor scores", "n": int(len(df))}, open(os.path.join(ART, "learned_weights.json"), "w"), indent=2)

    # ---- figures for the report
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(5.2, 4.4))
        for name in ["Lines only", "Rule-based health score (no learning)", "Logistic regression (all features)", "Gradient boosting (all features)"]:
            fpr, tpr, _ = roc_curve(y, oof[name])
            ax.plot(fpr, tpr, label=f"{name.split(' (')[0]} (AUC {results[name]['pooled_auc']:.2f})")
        ax.plot([0, 1], [0, 1], "k--", lw=0.8)
        ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate"); ax.set_title("Leave-one-repo-out ROC (pooled)")
        ax.legend(fontsize=7, loc="lower right"); fig.tight_layout(); fig.savefig(os.path.join(ART, "roc.png"), dpi=160); plt.close(fig)
        top = sorted(coefs.items(), key=lambda kv: -abs(kv[1]))[:12]
        fig, ax = plt.subplots(figsize=(5.6, 4.2))
        ax.barh([k for k, _ in top][::-1], [v for _, v in top][::-1], color=["#2f6fdb" if v > 0 else "#9aa" for _, v in top][::-1])
        ax.set_title("Standardised coefficients (positive = riskier)"); fig.tight_layout(); fig.savefig(os.path.join(ART, "coefficients.png"), dpi=160); plt.close(fig)
    except Exception as e:  # figures are optional
        print("figures skipped:", e)
    print("learned weights:", learned)
    print("saved ->", ART)


if __name__ == "__main__":
    main()
