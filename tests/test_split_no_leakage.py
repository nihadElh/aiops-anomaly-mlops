import pandas as pd

from aiops.data import stratified_split


def test_splits_are_disjoint_reproducible_and_stratified():
    df = pd.DataFrame({
        "BlockId": [f"blk_{i}" for i in range(1000)],
        "E1": [1] * 1000,
        "y": [0] * 970 + [1] * 30,
    })

    a = stratified_split(df, 0.70, 0.15, seed=42)
    b = stratified_split(df, 0.70, 0.15, seed=42)

    # Les tailles doivent respecter les proportions,
    # avec une tolérance pour les arrondis.
    expected = [700, 150, 150]

    for part, target_size in zip(a, expected):
        assert abs(len(part) - target_size) <= 1

    # Aucun bloc ne doit apparaître dans plusieurs ensembles.
    train_ids = set(a[0]["BlockId"])
    val_ids = set(a[1]["BlockId"])
    test_ids = set(a[2]["BlockId"])

    assert train_ids.isdisjoint(val_ids)
    assert train_ids.isdisjoint(test_ids)
    assert val_ids.isdisjoint(test_ids)

    # Aucun bloc perdu.
    assert sum(len(part) for part in a) == len(df)

    # Split reproductible avec la même seed.
    for first, second in zip(a, b):
        pd.testing.assert_frame_equal(first, second)

    # Proportions d'anomalies proches de la distribution initiale.
    original_rate = df["y"].mean()

    for part in a:
        assert abs(part["y"].mean() - original_rate) < 0.01