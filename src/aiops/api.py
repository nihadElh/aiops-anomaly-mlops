"""API FastAPI : /health, /predict, /metrics + journaux structurés (JSON lines)."""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .monitor import RuntimeMetrics


class PredictRequest(BaseModel):
    counts: list[float] = Field(
        ..., min_length=1, description="Occurrences de chaque type d'événement (E1..En) du bloc."
    )


class PredictResponse(BaseModel):
    request_id: str
    anomaly_score: float
    is_anomaly: bool
    threshold: float
    model_version: str


def create_app(model_path: str | None = None, log_path: str | None = None) -> FastAPI:
    model_path = model_path or os.getenv("MODEL_PATH", "artifacts/best_model.joblib")
    log_path = log_path or os.getenv("LOG_PATH", "logs/requests.jsonl")
    app = FastAPI(title="AIOps anomaly detector", version="0.1.0")
    runtime = RuntimeMetrics()
    cache: dict = {}

    def bundle() -> dict | None:
        if "b" not in cache and Path(model_path).exists():
            cache["b"] = joblib.load(model_path)
        return cache.get("b")

    def log_event(event: dict) -> None:
        # On ne journalise ni les entrées brutes ni de donnée personnelle : événements opérationnels.
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    @app.get("/health")
    def health():
        b = bundle()
        if b is None:
            raise HTTPException(status_code=503, detail="modèle non chargé")
        return {"status": "ok", "model": b["name"], "model_version": b["version"]}

    @app.post("/predict", response_model=PredictResponse)
    def predict(req: PredictRequest):
        t0 = time.perf_counter()
        rid = str(uuid.uuid4())
        b = bundle()
        if b is None:
            runtime.record_error()
            raise HTTPException(status_code=503, detail="modèle non chargé")
        n_expected = len(b["feature_cols"])
        if len(req.counts) != n_expected or min(req.counts) < 0:
            runtime.record_error()
            log_event({"request_id": rid, "status": "invalid_input"})
            raise HTTPException(
                status_code=422,
                detail=f"{n_expected} comptes positifs ou nuls attendus (E1..E{n_expected})",
            )
        x = np.asarray(req.counts, dtype=float).reshape(1, -1)
        import pandas as pd

        score = float(b["model"].predict_proba(pd.DataFrame(x, columns=b["feature_cols"]))[0, 1])
        is_anom = score >= b["threshold"]
        latency = (time.perf_counter() - t0) * 1000
        runtime.record(latency, score, is_anom)
        log_event({"request_id": rid, "status": "ok", "score": round(score, 5),
                   "is_anomaly": is_anom, "latency_ms": round(latency, 3),
                   "model_version": b["version"]})
        return PredictResponse(request_id=rid, anomaly_score=score, is_anomaly=is_anom,
                               threshold=b["threshold"], model_version=b["version"])

    @app.get("/metrics")
    def metrics():
        return runtime.snapshot()

    return app


app = create_app()
