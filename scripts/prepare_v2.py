
"""
LogGuard AI — Préparation des données V2.

Objectif :
- Séparer les données selon les patterns E1...E29.
- Garantir zéro pattern partagé entre train, val et test.
- Rechercher une répartition proche de 70/15/15.
- Limiter les écarts de taux d'anomalies.
- Conserver la V1 intacte.
- Enregistrer un manifest reproductible.

La sélection du split n'utilise aucune performance ML.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 42
N_CANDIDATES = 3000

SOURCE_DIR = Path("data/processed/v1")
OUTPUT_DIR = Path("data/processed/v2")

FEATURES = [f"E{i}" for i in range(1, 30)]

TARGET_RATIOS = np.array([0.70, 0.15, 0.15])

PARTITION_NAMES = ["train", "val", "test"]


def load_data():
    """Reconstituer le dataset complet depuis la V1."""

    frames = []

    for name in PARTITION_NAMES:
        path = SOURCE_DIR / f"{name}.parquet"

        if not path.exists():
            raise FileNotFoundError(
                f"Fichier V1 introuvable : {path}"
            )

        frames.append(pd.read_parquet(path))

    df = pd.concat(frames, ignore_index=True)

    required = FEATURES + ["y"]

    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(
            f"Colonnes manquantes : {missing}"
        )

    if df[required].isna().any().any():
        raise ValueError("Valeurs manquantes détectées.")

    if not df["y"].isin([0, 1]).all():
        raise ValueError(
            "La colonne y doit contenir uniquement 0 et 1."
        )

    return df


def build_pattern_groups(df):
    """
    Identifier les patterns identiques.

    factorize attribue un identifiant unique à chaque
    combinaison E1...E29.
    """

    pattern_index = pd.MultiIndex.from_frame(df[FEATURES])

    group_ids, _ = pd.factorize(
        pattern_index,
        sort=False,
    )

    summary = (
        pd.DataFrame({
            "group_id": group_ids,
            "y": df["y"].to_numpy(),
        })
        .groupby("group_id")
        .agg(
            rows=("y", "size"),
            anomalies=("y", "sum"),
        )
        .reset_index()
    )

    return group_ids, summary


def split_score(rows, anomalies, total_rows, global_rate):
    """
    Évaluer une proposition de split.

    On pénalise :
    1. Les écarts par rapport aux tailles 70/15/15.
    2. Les écarts de prévalence des anomalies.
    3. Les partitions sans anomalies.
    """

    actual_ratios = rows / total_rows

    size_error = np.sum(
        ((actual_ratios - TARGET_RATIOS) / TARGET_RATIOS) ** 2
    )

    rates = anomalies / np.maximum(rows, 1)

    prevalence_error = np.sum(
        ((rates - global_rate) / max(global_rate, 1e-12)) ** 2
    )

    missing_class_penalty = 100.0 * np.sum(
        (anomalies == 0) | (anomalies == rows)
    )

    return (
        4.0 * size_error
        + prevalence_error
        + missing_class_penalty
    )


def find_best_split(summary, total_rows, total_anomalies):
    """
    Rechercher plusieurs répartitions des groupes.

    Les groupes les plus volumineux sont placés en premier,
    puis les groupes restants sont distribués en minimisant
    le score de déséquilibre.
    """

    rng = np.random.default_rng(SEED)

    group_rows = summary["rows"].to_numpy()
    group_anomalies = summary["anomalies"].to_numpy()

    n_groups = len(summary)

    global_rate = total_anomalies / total_rows

    best_score = float("inf")
    best_assignment = None

    for candidate in range(N_CANDIDATES):

        # Perturbation aléatoire de l'ordre des groupes.
        # Les gros groupes restent généralement prioritaires.
        noise = rng.uniform(0.5, 1.5, size=n_groups)

        order = np.argsort(
            -(group_rows * noise)
        )

        assignment = np.full(n_groups, -1, dtype=int)

        rows = np.zeros(3, dtype=np.int64)
        anomalies = np.zeros(3, dtype=np.int64)

        for group in order:

            candidate_scores = []

            for partition in range(3):

                trial_rows = rows.copy()
                trial_anomalies = anomalies.copy()

                trial_rows[partition] += group_rows[group]
                trial_anomalies[partition] += group_anomalies[group]

                score = split_score(
                    trial_rows,
                    trial_anomalies,
                    total_rows,
                    global_rate,
                )

                # Légère perturbation pour explorer
                # différentes répartitions.
                score += rng.uniform(0, 0.0001)

                candidate_scores.append(score)

            selected = int(np.argmin(candidate_scores))

            assignment[group] = selected

            rows[selected] += group_rows[group]
            anomalies[selected] += group_anomalies[group]

        score = split_score(
            rows,
            anomalies,
            total_rows,
            global_rate,
        )

        if score < best_score:
            best_score = score
            best_assignment = assignment.copy()

    if best_assignment is None:
        raise RuntimeError(
            "Aucune répartition valide trouvée."
        )

    return best_assignment, best_score


def validate_split(df, group_ids, assignment):
    """Vérifier toutes les contraintes du split."""

    row_partitions = assignment[group_ids]

    if not np.isin(row_partitions, [0, 1, 2]).all():
        raise AssertionError(
            "Certaines lignes n'ont pas de partition."
        )

    pattern_sets = []

    for partition in range(3):

        indices = np.flatnonzero(
            row_partitions == partition
        )

        if len(indices) == 0:
            raise AssertionError(
                f"Partition vide : {PARTITION_NAMES[partition]}"
            )

        subset = df.iloc[indices]

        if subset["y"].nunique() != 2:
            raise AssertionError(
                f"Une classe manque dans "
                f"{PARTITION_NAMES[partition]}"
            )

        pattern_sets.append(
            set(group_ids[indices])
        )

    assert pattern_sets[0].isdisjoint(pattern_sets[1])
    assert pattern_sets[0].isdisjoint(pattern_sets[2])
    assert pattern_sets[1].isdisjoint(pattern_sets[2])

    return row_partitions


def save_partitions(df, group_ids, row_partitions, score):
    """Enregistrer les Parquet V2 et le manifest."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    global_rate = float(df["y"].mean())

    manifest = {
        "version": "V2",
        "split_strategy": "optimized_group_by_pattern",
        "seed": SEED,
        "n_candidates": N_CANDIDATES,
        "features": FEATURES,
        "n_rows": len(df),
        "n_unique_patterns": int(
            len(np.unique(group_ids))
        ),
        "global_anomaly_rate": global_rate,
        "target_ratios": {
            name: float(ratio)
            for name, ratio in zip(
                PARTITION_NAMES, TARGET_RATIOS
            )
        },
        "split_score": float(score),
        "partitions": {},
        "pattern_overlap": 0,
    }

    for partition, name in enumerate(PARTITION_NAMES):

        mask = row_partitions == partition

        subset = df.loc[mask].copy()

        path = OUTPUT_DIR / f"{name}.parquet"

        subset.to_parquet(path, index=False)

        n_rows = len(subset)
        n_anomalies = int(subset["y"].sum())

        manifest["partitions"][name] = {
            "rows": n_rows,
            "ratio": float(n_rows / len(df)),
            "anomalies": n_anomalies,
            "anomaly_rate": float(
                n_anomalies / n_rows
            ),
            "unique_patterns": int(
                len(np.unique(group_ids[mask]))
            ),
        }

    manifest_path = OUTPUT_DIR / "manifest.json"

    manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print("\n=== LOGGUARD AI — V2 SPLIT ===")
    print(json.dumps(manifest, indent=2))

    print("\nVérifications terminées :")
    print("- Toutes les lignes sont réparties")
    print("- Les trois partitions contiennent les deux classes")
    print("- Aucun pattern partagé")
    print("- V1 conservée")


def main():

    print("Chargement des données V1...")

    df = load_data()

    print("Identification des patterns...")

    group_ids, summary = build_pattern_groups(df)

    print(
        f"{len(df):,} blocs | "
        f"{len(summary)} patterns uniques"
    )

    print(
        f"Recherche de {N_CANDIDATES} splits candidats..."
    )

    assignment, score = find_best_split(
        summary,
        total_rows=len(df),
        total_anomalies=int(df["y"].sum()),
    )

    row_partitions = validate_split(
        df,
        group_ids,
        assignment,
    )

    save_partitions(
        df,
        group_ids,
        row_partitions,
        score,
    )


if __name__ == "__main__":
    main()
