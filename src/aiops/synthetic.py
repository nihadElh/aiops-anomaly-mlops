"""Données synthétiques au format « occurrence matrix » : UNIQUEMENT pour tests et CI.

Ne jamais présenter ces données comme des résultats réels dans le rapport.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def make_synthetic(
    n: int = 3000, n_events: int = 29, anomaly_rate: float = 0.03, seed: int = 42
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    normal_p = rng.dirichlet(np.ones(n_events) * 2)
    anomal_p = normal_p.copy()
    boosted = rng.choice(n_events, size=4, replace=False)
    anomal_p[boosted] *= 6
    anomal_p /= anomal_p.sum()

    y = rng.random(n) < anomaly_rate
    y[:5] = False
    y[5:15] = True  # garantit des anomalies même sur de petits échantillons
    rows = []
    for is_anom in y:
        total = int(rng.integers(8, 40))
        rows.append(rng.multinomial(total, anomal_p if is_anom else normal_p))
    df = pd.DataFrame(rows, columns=[f"E{i + 1}" for i in range(n_events)])
    df.insert(0, "Label", np.where(y, "Anomaly", "Normal"))
    df.insert(0, "BlockId", [f"blk_{i}" for i in range(n)])
    # mélange : les anomalies sont réparties dans le temps (chaque split en contient)
    return df.sample(frac=1.0, random_state=seed).reset_index(drop=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/sample/sample.csv")
    ap.add_argument("--n", type=int, default=3000)
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    make_synthetic(args.n).to_csv(out, index=False)
    print(f"écrit : {out}")
