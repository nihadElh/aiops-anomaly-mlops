"""Préparation HDFS_v1: jointure sûre, contrôle anti-fuite, split stratifié."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from .config import load_params
from .validate import assert_valid


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def add_binary_label(df: pd.DataFrame, label_col: str, positive_label: str) -> pd.DataFrame:
    out = df.copy()
    out['y'] = (out[label_col].astype(str) == positive_label).astype('int8')
    return out


def stratified_split(df: pd.DataFrame, train_frac: float, val_frac: float, seed: int):
    if not (0 < train_frac < 1 and 0 < val_frac < 1 and train_frac + val_frac < 1):
        raise ValueError('Fractions train/val invalides.')
    train, remaining = train_test_split(
        df, train_size=train_frac, stratify=df['y'], random_state=seed
    )
    val_share = val_frac / (1 - train_frac)
    val, test = train_test_split(
        remaining, train_size=val_share, stratify=remaining['y'], random_state=seed
    )
    return tuple(part.reset_index(drop=True) for part in (train, val, test))


def prepare(raw_path: str | Path, out_dir: str | Path, params: dict) -> dict:
    cfg = params['data']
    matrix_path = Path(raw_path)
    labels_path = Path(cfg['labels_path'])
    id_col = cfg['id_col']
    label_col = cfg['label_col']
    feature_regex = cfg['feature_regex']

    # Lecture explicite des types et colonnes: ne jamais importer Label/Type de la matrice.
    matrix_header = pd.read_csv(matrix_path, nrows=0).columns.tolist()
    feature_cols = sorted(
        [c for c in matrix_header if re.fullmatch(feature_regex, c)],
        key=lambda c: int(c[1:]),
    )
    if not feature_cols:
        raise ValueError('Aucune colonne événement E1...En trouvée.')
    if id_col not in matrix_header:
        raise ValueError(f'Identifiant absent de la matrice : {id_col}')

    matrix = pd.read_csv(matrix_path, usecols=[id_col, *feature_cols], dtype={id_col: 'string'})
    labels = pd.read_csv(labels_path, usecols=[id_col, label_col], dtype={id_col: 'string'})

    if matrix[id_col].isna().any() or labels[id_col].isna().any():
        raise ValueError('BlockId manquant dans une source.')
    if matrix[id_col].duplicated().any() or labels[id_col].duplicated().any():
        raise ValueError('BlockId dupliqué dans une source.')

    # Jointure 1:1, avec vérification stricte des blocs manquants de part et d'autre.
    df = matrix.merge(labels, on=id_col, how='outer', validate='one_to_one', indicator=True)
    unmatched = df['_merge'].value_counts().to_dict()
    if unmatched.get('left_only', 0) or unmatched.get('right_only', 0):
        raise ValueError(f'Jointure incomplète entre matrice et labels : {unmatched}')
    df = df.drop(columns='_merge')

    assert_valid(
        df, id_col=id_col, label_col=label_col,
        feature_regex=feature_regex, allowed_labels=cfg['allowed_labels'],
    )
    df = add_binary_label(df, label_col, cfg['positive_label'])

    # Conserver uniquement les features et la cible, jamais Label/Type en entrée modèle.
    df = df[[id_col, *feature_cols, 'y']]
    if set(df['y'].unique()) != {0, 1}:
        raise ValueError('Les deux classes doivent être présentes.')

    train, val, test = stratified_split(
        df, params['split']['train_frac'], params['split']['val_frac'], params['seed']
    )
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        'source_sha256': {
            'matrix': file_sha256(matrix_path),
            'labels': file_sha256(labels_path),
        },
        'raw_sha256': file_sha256(matrix_path),  # Compatibilité avec train.py existant.
        'split_strategy': 'stratified_random_by_block',
        'seed': params['seed'],
        'n_rows': len(df),
        'feature_columns': feature_cols,
        'n_features': len(feature_cols),
        'positive_label': cfg['positive_label'],
    }
    for name, part in [('train', train), ('val', val), ('test', test)]:
        if part['y'].sum() == 0:
            raise ValueError(f'Aucune anomalie dans le split {name}.')
        part.to_parquet(out / f'{name}.parquet', index=False)
        manifest[name] = {
            'rows': len(part),
            'anomalies': int(part['y'].sum()),
            'anomaly_rate': round(float(part['y'].mean()), 6),
        }
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


def main() -> None:
    params = load_params()
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw', default=params['data']['raw_path'])
    parser.add_argument('--out', default=params['data']['processed_dir'])
    args = parser.parse_args()
    print(json.dumps(prepare(args.raw, args.out, params), indent=2))


if __name__ == '__main__':
    main()
