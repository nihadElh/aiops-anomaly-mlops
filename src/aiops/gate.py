"""Quality gate « Modèle » : refuse la promotion d'une version dégradée (exit code 1)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .config import load_params


def check_gate(test_metrics: dict, cfg: dict) -> tuple[bool, list[str]]:
    cand_name = test_metrics["best"]
    cand = test_metrics[cand_name]
    base = test_metrics[cfg["baseline"]]
    failures: list[str] = []
    gain = cand["pr_auc"] - base["pr_auc"]
    if cand_name != cfg["baseline"] and gain < cfg["min_pr_auc_gain"]:
        failures.append(f"gain PR-AUC {gain:.4f} < {cfg['min_pr_auc_gain']} vs baseline")
    if cand["recall"] < cfg["min_recall"]:
        failures.append(f"rappel {cand['recall']:.3f} < {cfg['min_recall']}")
    if cand["precision"] < cfg["min_precision"]:
        failures.append(f"précision {cand['precision']:.3f} < {cfg['min_precision']}")
    return (not failures), failures


def main() -> int:
    p = load_params()
    metrics = json.loads(Path("artifacts/test_metrics.json").read_text(encoding="utf-8"))
    ok, failures = check_gate(metrics, p["quality_gate"])
    print("QUALITY GATE :", "ACCEPTÉ" if ok else "REJETÉ")
    for f in failures:
        print(" -", f)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
