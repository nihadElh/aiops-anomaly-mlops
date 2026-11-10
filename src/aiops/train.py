
"""Entraînement, validation et suivi automatique des expériences MLflow."""

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


EXPERIMENT_NAME = "HDFS_V1_Block_Stratified"


def git_commit() -> str:
    """Récupère le commit Git courant."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def default_tracking_uri() -> str:
    """Utilise une base SQLite locale avec un chemin absolu."""
    database = (Path.cwd() / "mlflow_tracking.db").resolve()
    return f"sqlite:///{database.as_posix()}"


def configure_mlflow(
    tracking_uri: str | None = None,
    experiment: str = EXPERIMENT_NAME,
) -> str:
    """Configure MLflow et crée l'expérience si nécessaire."""
    uri = tracking_uri or os.getenv(
        "MLFLOW_TRACKING_URI"
    ) or default_tracking_uri()

    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(experiment)

    print(f"[MLflow] Tracking URI: {uri}")
    print(f"[MLflow] Experiment: {experiment}")

    return uri


def build_models(params: dict) -> dict:
    """Construit les deux modèles avec les paramètres YAML."""
    seed = params["seed"]
    models_params = params["models"]

    return {
        "logreg": Pipeline(
            [
                (
                    "log1p",
                    FunctionTransformer(np.log1p, validate=False),
                ),
                ("scale", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        **models_params["logreg"],
                        random_state=seed,
                    ),
                ),
            ]
        ),
        "gbm": HistGradientBoostingClassifier(
            **models_params["gbm"],
            random_state=seed,
        ),
    }


def run_training(
    params: dict,
    train: pd.DataFrame,
    val: pd.DataFrame,
    artifacts_dir: str | Path,
    tracking_uri: str | None = None,
    data_sha: str = "unknown",
    experiment: str = EXPERIMENT_NAME,
    register: bool = False,
) -> dict:
    """
    Entraîne les modèles et enregistre les expériences MLflow.

    Le modèle et son seuil sont sélectionnés uniquement
    à partir des données de validation.
    """
    artifacts_dir = Path(artifacts_dir)
    models_dir = artifacts_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    features = feature_columns(
        train,
        params["data"]["feature_regex"],
    )

    if not features:
        raise ValueError("Aucune feature détectée.")

    if not {"y", *features}.issubset(val.columns):
        raise ValueError(
            "Le jeu de validation ne contient pas "
            "toutes les colonnes attendues."
        )

    x_train = train[features]
    y_train = train["y"].astype(int)

    x_val = val[features]
    y_val = val["y"].astype(int)

    if y_train.nunique() < 2 or y_val.nunique() < 2:
        raise ValueError(
            "Train et validation doivent contenir "
            "les deux classes."
        )

    configure_mlflow(tracking_uri, experiment)

    results = {}
    run_ids = {}

    for name, model in build_models(params).items():

        print(f"\n{'=' * 50}")
        print(f"Entraînement du modèle : {name}")
        print(f"{'=' * 50}")

        with mlflow.start_run(run_name=f"V1_{name}") as run:

            # 1. Entraînement
            model.fit(x_train, y_train)

            # 2. Prédictions sur validation
            scores = model.predict_proba(x_val)[:, 1]

            # 3. Optimisation du seuil sur validation
            threshold = float(
                best_f1_threshold(y_val, scores)
            )

            # 4. Calcul des métriques
            metrics = evaluate_scores(
                y_val,
                scores,
                threshold,
            )

            # 5. Paramètres et contexte
            mlflow.log_params({
                **{
                    f"model_{key}": value
                    for key, value
                    in params["models"][name].items()
                },
                "seed": params["seed"],
                "model_type": name,
                "n_features": len(features),
                "n_train": len(train),
                "n_val": len(val),
                "split_strategy": "stratified_random_by_block",
            })

            # 6. Métriques de validation
            for key, value in metrics.items():
                if (
                    isinstance(value, (int, float, np.number))
                    and not isinstance(value, (bool, np.bool_))
                ):
                    mlflow.log_metric(
                        f"val_{key}",
                        float(value),
                    )

            # 7. Métadonnées de reproductibilité
            mlflow.set_tags({
                "project": "LogGuard AI",
                "dataset": "HDFS_v1",
                "experiment_version": "V1",
                "split_strategy": "stratified_random_by_block",
                "git_commit": git_commit(),
                "data_sha256": data_sha,
                "evaluation_dataset": "validation",
            })

            # 8. Sauvegarde du modèle dans MLflow
            mlflow.sklearn.log_model(
                sk_model=model,
                artifact_path="model",
            )

            # 9. Sauvegarde du bundle local
            bundle = {
                "name": name,
                "model": model,
                "feature_cols": features,
                "threshold": threshold,
                "version": f"{git_commit()}-{data_sha[:8]}",
                "trained_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            local_model_path = (
                models_dir / f"{name}.joblib"
            )

            joblib.dump(bundle, local_model_path)

            # 10. Enregistrement des features et métriques
            mlflow.log_dict(
                {
                    "model": name,
                    "features": features,
                    "threshold": threshold,
                    "validation_metrics": metrics,
                },
                "validation_summary.json",
            )

            # 11. Traçabilité du run
            run_ids[name] = run.info.run_id
            results[name] = metrics

            print(f"Run ID : {run.info.run_id}")
            print(f"AP     : {metrics['pr_auc']:.6f}")
            print(f"Recall : {metrics['recall']:.6f}")
            print(f"F1     : {metrics['f1']:.6f}")

    # Sélection sur la validation uniquement
    best_model = max(
        results,
        key=lambda name: results[name]["pr_auc"],
    )

    shutil.copy2(
        models_dir / f"{best_model}.joblib",
        artifacts_dir / "best_model.joblib",
    )

    results["best"] = best_model

    metrics_path = artifacts_dir / "val_metrics.json"
    metrics_path.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    # Enregistrement facultatif au Model Registry
    if register:
        mlflow.register_model(
            model_uri=f"runs:/{run_ids[best_model]}/model",
            name="aiops-anomaly-detector",
        )

    print("\nEntraînement terminé.")
    print(f"Meilleur modèle : {best_model}")
    print(f"Métriques : {metrics_path}")

    return results


def main() -> None:
    params = load_params()

    processed_dir = Path(
        params["data"]["processed_dir"]
    )

    manifest = json.loads(
        (processed_dir / "manifest.json").read_text(
            encoding="utf-8"
        )
    )

    results = run_training(
        params=params,
        train=pd.read_parquet(
            processed_dir / "train.parquet"
        ),
        val=pd.read_parquet(
            processed_dir / "val.parquet"
        ),
        artifacts_dir="artifacts",
        tracking_uri=None,
        data_sha=manifest["raw_sha256"],
        experiment=EXPERIMENT_NAME,
        register=False,
    )

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
