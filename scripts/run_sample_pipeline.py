"""Pipeline complet sur données SYNTHÉTIQUES (smoke test CI) : prepare -> train -> evaluate -> gate."""
import sys
from pathlib import Path

import pandas as pd

from aiops.config import load_params
from aiops.data import prepare
from aiops.evaluate import run_evaluation
from aiops.gate import check_gate
from aiops.synthetic import make_synthetic
from aiops.train import run_training

work = Path(".sample_run")
work.mkdir(exist_ok=True)
params = load_params()
raw = work / "sample.csv"
make_synthetic(4000).to_csv(raw, index=False)
manifest = prepare(raw, work / "processed", params)
train = pd.read_parquet(work / "processed" / "train.parquet")
val = pd.read_parquet(work / "processed" / "val.parquet")
test = pd.read_parquet(work / "processed" / "test.parquet")
run_training(params, train, val, work / "artifacts", f"sqlite:///{work / 'mlflow.db'}",
             data_sha=manifest["raw_sha256"], register=False)
res = run_evaluation(work / "artifacts", test)
ok, failures = check_gate(res, params["quality_gate"])
print("GATE :", "ACCEPTÉ" if ok else f"REJETÉ {failures}")
sys.exit(0 if ok else 1)
