"""Métriques adaptées au déséquilibre de classes (PR-AUC, précision, rappel, F1)."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    precision_recall_fscore_support,
)


def best_f1_threshold(y_true, scores) -> float:
    """Seuil maximisant le F1 — à choisir sur la VALIDATION uniquement, jamais sur le test."""
    precision, recall, thresholds = precision_recall_curve(y_true, scores)
    p, r = precision[:-1], recall[:-1]
    f1 = np.where(p + r > 0, 2 * p * r / (p + r + 1e-12), 0.0)
    return float(thresholds[int(np.argmax(f1))])


def evaluate_scores(y_true, scores, threshold: float) -> dict:
    y_true = np.asarray(y_true)
    pred = (np.asarray(scores) >= threshold).astype(int)
    p, r, f1, _ = precision_recall_fscore_support(
        y_true, pred, average="binary", zero_division=0
    )
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    return {
        "pr_auc": float(average_precision_score(y_true, scores)),
        "precision": float(p),
        "recall": float(r),
        "f1": float(f1),
        "threshold": float(threshold),
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        "positive_rate": float(y_true.mean()),
    }
