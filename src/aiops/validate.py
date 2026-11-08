"""Quality gate « Données » : schéma, valeurs manquantes, doublons, labels."""
from __future__ import annotations

import re

import pandas as pd


def feature_columns(df: pd.DataFrame, feature_regex: str) -> list[str]:
    return [c for c in df.columns if re.match(feature_regex, c)]


def validate_schema(
    df: pd.DataFrame,
    id_col: str,
    label_col: str,
    feature_regex: str,
    allowed_labels: list[str],
) -> list[str]:
    """Retourne la liste des erreurs (vide si les données sont valides)."""
    errors: list[str] = []
    for col in (id_col, label_col):
        if col not in df.columns:
            errors.append(f"colonne manquante : {col}")
    feats = feature_columns(df, feature_regex)
    if not feats:
        errors.append("aucune colonne de features détectée")
    if errors:
        return errors
    if df[id_col].duplicated().any():
        errors.append("identifiants dupliqués")
    if df[label_col].isna().any():
        errors.append("labels manquants")
    unknown = set(df[label_col].dropna().astype(str)) - set(allowed_labels)
    if unknown:
        errors.append(f"labels inattendus : {sorted(unknown)}")
    if not all(pd.api.types.is_numeric_dtype(df[c]) for c in feats):
        errors.append("features non numériques")
    else:
        if df[feats].isna().any().any():
            errors.append("valeurs manquantes dans les features")
        if (df[feats] < 0).any().any():
            errors.append("comptes négatifs dans les features")
    return errors


def assert_valid(df: pd.DataFrame, **kwargs) -> None:
    errors = validate_schema(df, **kwargs)
    if errors:
        raise ValueError("Données invalides :\n- " + "\n- ".join(errors))
