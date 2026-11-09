from fastapi import APIRouter, HTTPException

from ml.model import get_model

router = APIRouter(prefix="/api/model", tags=["model"])


@router.get("")
def model_card():
    """Model card: what the defect-risk model is, how it was trained and how well it did on held-out repositories."""
    m = get_model()
    if m is None:
        raise HTTPException(503, detail={"message": "Model artifacts not found. Run `python -m ml.train`."})
    meta = m.meta
    models = {k: {"auc": round(v["auc_mean"], 3), "auc_std": round(v["auc_std"], 3), "average_precision": round(v["ap_mean"], 3),
                  "precision_at_20": round(v["p20_mean"], 3), "recall_at_20": round(v["r20_mean"], 3)} for k, v in meta["models"].items()}
    coefs = sorted(meta["coefficients"].items(), key=lambda kv: -abs(kv[1]))
    return {**m.card(), "base_rate": round(meta["base_rate"], 4), "per_repo": meta["repos"], "comparison": models,
            "coefficients": [{"feature": k, "weight": round(v, 3)} for k, v in coefs],
            "hand_weights": meta["hand_weights"], "learned_weights": meta["learned_weights"],
            "label_definition": "A function is labelled defective if a later bug-fix commit changed or deleted one of its lines (SZZ-style, message heuristics).",
            "caveats": ["Labels come from commit-message heuristics and are noisy.", "Trained on 11 open-source Python libraries; may not transfer to other domains.",
                        "Probability is relative: it is the chance a bug-fix touches the function, among files that a fix touched."]}
