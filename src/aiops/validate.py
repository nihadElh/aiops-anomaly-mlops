
"""Validation du schéma et de la qualité des données HDFS."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd


def feature_columns(
    df: pd.DataFrame,
    feature_regex: str,
) -> list[str]:
    """Retourne les features correspondant exactement au regex."""
    pattern = re.compile(feature_regex)

    columns = [
        col for col in df.columns
        if pattern.fullmatch(str(col))
    ]

    return sorted(
        columns,
        key=lambda col: (
            int(col[1:])
            if re.fullmatch(r"E\d+", col)
            else str(col)
        ),
    )


def validate_schema(
    df: pd.DataFrame,
    id_col: str,
    label_col: str,
    feature_regex: str,
    allowed_labels: list[str],
) -> list[str]:
    """
    Vérifie le schéma et la qualité des données.

    Retourne une liste d'erreurs.
    Une liste vide signifie que les contrôles ont réussi.
    """
    errors = []

    # 1. Colonnes obligatoires
    for col in (id_col, label_col):
        if col not in df.columns:
            errors.append(f"Colonne manquante : {col}")

    features = feature_columns(df, feature_regex)

    if not features:
        errors.append("Aucune feature détectée.")

    if errors:
        return errors

    # 2. Identifiants
    if df[id_col].isna().any():
        errors.append("Identifiants manquants.")

    if df[id_col].duplicated().any():
        errors.append("Identifiants dupliqués.")

    # 3. Labels
    if df[label_col].isna().any():
        errors.append("Labels manquants.")

    unknown_labels = (
        set(df[label_col].dropna().astype(str))
        - set(allowed_labels)
    )

    if unknown_labels:
        errors.append(
            f"Labels inattendus : {sorted(unknown_labels)}"
        )

    # 4. Types numériques
    non_numeric = [
        col for col in features
        if not pd.api.types.is_numeric_dtype(df[col])
    ]

    if non_numeric:
        errors.append(
            f"Features non numériques : {non_numeric}"
        )
        return errors

    # 5. Valeurs manquantes
    if df[features].isna().any().any():
        errors.append(
            "Valeurs manquantes dans les features."
        )

    # 6. Valeurs infinies
    numeric_values = df[features].to_numpy(
        dtype=float
    )

    if np.isinf(numeric_values).any():
        errors.append(
            "Valeurs infinies dans les features."
        )

    # 7. Comptages négatifs
    if (df[features] < 0).any().any():
        errors.append(
            "Comptages négatifs dans les features."
        )

    return errors


def assert_valid(
    df: pd.DataFrame,
    **kwargs,
) -> None:
    """Déclenche une erreur si les données sont invalides."""
    errors = validate_schema(df, **kwargs)

    if errors:
        raise ValueError(
            "Données invalides :\n- "
            + "\n- ".join(errors)
        )
