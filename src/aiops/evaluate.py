"""Évaluation finale sur le TEST (à n'exécuter qu'une fois le choix du modèle figé)."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

from .config import load_params
from .metrics import evaluate_scores


def run_evaluation(artifacts_dir: str | Path, test: pd.DataFrame) -> dict:
    art = Path(artifacts_dir)
    results: dict = {}
    for path in sorted((art / "models").glob("*.joblib")):
        b = joblib.load(path)
        scores = b["model"].predict_proba(test[b["feature_cols"]])[:, 1]
        results[b["name"]] = evaluate_scores(test["y"], scores, b["threshold"])
    results["best"] = json.loads((art / "val_metrics.json").read_text())["best"]
    (art / "test_metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    p = load_params()
    test_df = pd.read_parquet(Path(p["data"]["processed_dir"]) / "test.parquet")
    print(json.dumps(run_evaluation("artifacts", test_df), indent=2))
