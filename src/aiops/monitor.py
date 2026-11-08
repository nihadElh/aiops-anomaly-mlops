"""Monitoring : dérive des entrées/scores (PSI) et métriques d'exécution de l'API."""
from __future__ import annotations

import json
import threading
from pathlib import Path

import numpy as np
import pandas as pd


def psi(reference, current, bins: int = 10) -> float:
    """Population Stability Index. <0.10 stable, 0.10-0.25 à surveiller, >0.25 dérive forte."""
    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(current, dtype=float)
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:  # variable quasi constante
        return 0.0 if np.allclose(ref.mean(), cur.mean()) else 1.0
    edges[0], edges[-1] = -np.inf, np.inf
    r = np.histogram(ref, edges)[0] / len(ref)
    c = np.histogram(cur, edges)[0] / len(cur)
    r, c = np.clip(r, 1e-6, None), np.clip(c, 1e-6, None)
    return float(np.sum((c - r) * np.log(c / r)))


def unseen_event_rate(train_x: pd.DataFrame, new_x: pd.DataFrame) -> float:
    """Part des lignes contenant un type d'événement jamais observé à l'entraînement."""
    never_seen = [c for c in train_x.columns if train_x[c].sum() == 0]
    if not never_seen:
        return 0.0
    return float((new_x[never_seen].sum(axis=1) > 0).mean())


def drift_report(train_x: pd.DataFrame, new_x: pd.DataFrame, scores_ref, scores_new,
                 warning: float = 0.10, alert: float = 0.25) -> dict:
    per_feat = {c: psi(train_x[c], new_x[c]) for c in train_x.columns}
    worst = max(per_feat, key=per_feat.get)
    score_psi = psi(scores_ref, scores_new)
    status = "alert" if max(per_feat[worst], score_psi) > alert else (
        "warning" if max(per_feat[worst], score_psi) > warning else "stable")
    return {
        "status": status,
        "max_feature_psi": per_feat[worst],
        "max_feature": worst,
        "score_psi": score_psi,
        "unseen_event_rate": unseen_event_rate(train_x, new_x),
        "missing_rate": float(new_x.isna().mean().mean()),
    }


class RuntimeMetrics:
    """Indicateurs d'exécution de l'API : volume, erreurs, latence moyenne/P95, taux d'anomalies."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.latencies: list[float] = []
        self.scores: list[float] = []
        self.flags: list[int] = []
        self.n_errors = 0

    def record(self, latency_ms: float, score: float, is_anomaly: bool) -> None:
        with self._lock:
            self.latencies.append(latency_ms)
            self.scores.append(score)
            self.flags.append(int(is_anomaly))

    def record_error(self) -> None:
        with self._lock:
            self.n_errors += 1

    def snapshot(self) -> dict:
        with self._lock:
            n_ok, n_err = len(self.latencies), self.n_errors
            total = n_ok + n_err
            return {
                "n_requests": total,
                "n_errors": n_err,
                "error_rate": (n_err / total) if total else 0.0,
                "latency_ms_mean": float(np.mean(self.latencies)) if n_ok else 0.0,
                "latency_ms_p95": float(np.percentile(self.latencies, 95)) if n_ok else 0.0,
                "anomaly_rate": float(np.mean(self.flags)) if n_ok else 0.0,
                "mean_score": float(np.mean(self.scores)) if n_ok else 0.0,
            }


def main() -> None:
    """Simule un suivi en production : référence = train, courant = test, puis dérive injectée."""
    import joblib

    from .config import load_params

    p = load_params()
    proc = Path(p["data"]["processed_dir"])
    b = joblib.load("artifacts/best_model.joblib")
    fc = b["feature_cols"]
    train, test = pd.read_parquet(proc / "train.parquet"), pd.read_parquet(proc / "test.parquet")
    s_ref = b["model"].predict_proba(train[fc])[:, 1]
    mon = p["monitoring"]

    shifted = test[fc].copy()
    shifted.iloc[:, :5] = shifted.iloc[:, :5] * 3  # dérive simulée : 5 types d'événements ×3
    report = {
        "test_vs_train": drift_report(train[fc], test[fc], s_ref,
                                      b["model"].predict_proba(test[fc])[:, 1],
                                      mon["psi_warning"], mon["psi_alert"]),
        "simulated_shift": drift_report(train[fc], shifted, s_ref,
                                        b["model"].predict_proba(shifted)[:, 1],
                                        mon["psi_warning"], mon["psi_alert"]),
    }
    Path("artifacts/drift_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
