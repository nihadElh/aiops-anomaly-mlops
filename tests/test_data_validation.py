import pytest

from aiops.synthetic import make_synthetic
from aiops.validate import assert_valid, validate_schema

KW = {
    "id_col": "BlockId",
    "label_col": "Label",
    "feature_regex": r"^E\d+$",
    "allowed_labels": ["Normal", "Anomaly"],
}


def test_valid_data_has_no_errors():
    assert validate_schema(make_synthetic(500), **KW) == []


def test_missing_label_column_detected():
    df = make_synthetic(200).drop(columns=["Label"])
    assert any("Label" in e for e in validate_schema(df, **KW))


def test_duplicate_ids_detected():
    df = make_synthetic(200)
    df.loc[1, "BlockId"] = df.loc[0, "BlockId"]
    assert any("dupliqu" in e for e in validate_schema(df, **KW))


def test_negative_counts_detected():
    df = make_synthetic(200)
    df.loc[0, "E1"] = -1
    assert any("négatifs" in e for e in validate_schema(df, **KW))


def test_unknown_label_detected():
    df = make_synthetic(200)
    df.loc[0, "Label"] = "Weird"
    with pytest.raises(ValueError):
        assert_valid(df, **KW)
