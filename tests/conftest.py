import pandas as pd
import pytest

from aiops.config import load_params
from aiops.data import prepare
from aiops.synthetic import make_synthetic
from aiops.train import run_training


@pytest.fixture(scope="session")
def params():
    return load_params()


@pytest.fixture(scope="session")
def trained(tmp_path_factory, params):
    """Pipeline complet sur données synthétiques, dans un dossier temporaire."""
    work = tmp_path_factory.mktemp("run")
    raw = work / "sample.csv"
    labels_path = work / "anomaly_label.csv"

    # Générer les données synthétiques
    synthetic_df = make_synthetic(3000)

    # Créer un fichier de labels indépendant
    synthetic_df[["BlockId", "Label"]].to_csv(
        labels_path,
        index=False
    )

    # Créer une matrice d'événements sans la cible
    feature_cols = [
        col for col in synthetic_df.columns
        if col.startswith("E") and col[1:].isdigit()
    ]

    synthetic_df[["BlockId", *feature_cols]].to_csv(
        raw,
        index=False
    )

    # Utiliser les labels synthétiques uniquement pour ce test
    test_params = {
        **params,
        "data": {
            **params["data"],
            "labels_path": str(labels_path),
        },
    }

    manifest = prepare(raw, work / "processed", test_params)
    train = pd.read_parquet(work / "processed" / "train.parquet")
    val = pd.read_parquet(work / "processed" / "val.parquet")
    test = pd.read_parquet(work / "processed" / "test.parquet")
    art = work / "artifacts"
    res = run_training(params, train, val, art, f"sqlite:///{work / 'mlflow.db'}",
                       data_sha=manifest["raw_sha256"], register=False)
    return {"work": work, "art": art, "val_res": res, "train": train, "val": val, "test": test}
