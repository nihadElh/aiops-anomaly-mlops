"""Entraînement de 2 modèles (baseline + candidat), suivi MLflow, sélection sur validation."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from .config import load_params
from .metrics import best_f1_threshold, evaluate_scores
from .validate import feature_columns


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build_models(params: dict) -> dict:
    seed = params["seed"]
    m = params["models"]
    return {
        "logreg": Pipeline(
            [
                ("log1p", FunctionTransformer(np.log1p, validate=False)),
                ("scale", StandardScaler()),
                ("clf", LogisticRegression(**m["logreg"], random_state=seed)),
            ]
        ),
        "gbm": HistGradientBoostingClassifier(**m["gbm"], random_state=seed),
    }


def run_training(
    params: dict,
    train: pd.DataFrame,
    val: pd.DataFrame,
    artifacts_dir: str | Path,
    tracking_uri: str,
    data_sha: str = "unknown",
    experiment: str = "aiops-anomaly",
    register: bool = True,
) -> dict:
    art = Path(artifacts_dir)
    (art / "models").mkdir(parents=True, exist_ok=True)
    feats = feature_columns(train, params["data"]["feature_regex"])
    x_tr, y_tr = train[feats], train["y"]
    x_va, y_va = val[feats], val["y"]

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment)
    results: dict = {}
    run_ids: dict = {}
    for name, model in build_models(params).items():
        with mlflow.start_run(run_name=name) as run:
            model.fit(x_tr, y_tr)
            scores = model.predict_proba(x_va)[:, 1]
            thr = best_f1_threshold(y_va, scores)
            met = evaluate_scores(y_va, scores, thr)

            mlflow.log_params({f"{name}.{k}": v for k, v in params["models"][name].items()})
            mlflow.log_param("seed", params["seed"])
            mlflow.log_metrics({f"val_{k}": v for k, v in met.items() if isinstance(v, float)})
            mlflow.set_tags({"git_commit": git_commit(), "data_sha256": data_sha[:12]})
            mlflow.sklearn.log_model(model, "model")
            run_ids[name] = run.info.run_id

            bundle = {
                "name": name,
                "model": model,
                "feature_cols": feats,
                "threshold": thr,
                "version": f"{git_commit()}-{data_sha[:8]}",
                "trained_at": datetime.now(timezone.utc).isoformat(),
            }
            joblib.dump(bundle, art / "models" / f"{name}.joblib")
            results[name] = met

    best = max(results, key=lambda k: results[k]["pr_auc"])
    shutil.copy(art / "models" / f"{best}.joblib", art / "best_model.joblib")
    results["best"] = best
    (art / "val_metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    if register:
        mlflow.register_model(f"runs:/{run_ids[best]}/model", "aiops-anomaly-detector")
    return results


def main() -> None:
    p = load_params()
    proc = Path(p["data"]["processed_dir"])
    manifest = json.loads((proc / "manifest.json").read_text(encoding="utf-8"))
    res = run_training(
        p,
        pd.read_parquet(proc / "train.parquet"),
        pd.read_parquet(proc / "val.parquet"),
        "artifacts",
        os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"),
        data_sha=manifest["raw_sha256"],
    )
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
