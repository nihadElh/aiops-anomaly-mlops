from pathlib import Path

import yaml


def load_params(path: str | Path = "params.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
