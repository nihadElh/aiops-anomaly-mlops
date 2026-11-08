import json

from aiops.evaluate import run_evaluation
from aiops.gate import check_gate


def test_training_produces_artifacts(trained):
    art = trained["art"]
    assert (art / "best_model.joblib").exists()
    assert (art / "val_metrics.json").exists()
    assert {"logreg", "gbm", "best"} <= set(trained["val_res"])


def test_model_beats_random_on_synthetic(trained):
    best = trained["val_res"]["best"]
    # un classifieur aléatoire a une PR-AUC ~ taux d'anomalies
    assert trained["val_res"][best]["pr_auc"] > 3 * trained["val_res"][best]["positive_rate"]


def test_evaluation_writes_test_metrics(trained):
    res = run_evaluation(trained["art"], trained["test"])
    assert (trained["art"] / "test_metrics.json").exists()
    assert json.loads((trained["art"] / "test_metrics.json").read_text())["best"] == res["best"]


def test_gate_accepts_good_candidate():
    m = {"best": "gbm",
         "gbm": {"pr_auc": 0.9, "recall": 0.9, "precision": 0.9},
         "logreg": {"pr_auc": 0.8, "recall": 0.7, "precision": 0.7}}
    cfg = {"baseline": "logreg", "min_pr_auc_gain": 0.0, "min_recall": 0.5, "min_precision": 0.5}
    assert check_gate(m, cfg)[0]


def test_gate_rejects_degraded_candidate():
    m = {"best": "gbm",
         "gbm": {"pr_auc": 0.5, "recall": 0.2, "precision": 0.9},
         "logreg": {"pr_auc": 0.8, "recall": 0.7, "precision": 0.7}}
    cfg = {"baseline": "logreg", "min_pr_auc_gain": 0.0, "min_recall": 0.5, "min_precision": 0.5}
    ok, failures = check_gate(m, cfg)
    assert not ok and len(failures) >= 2
