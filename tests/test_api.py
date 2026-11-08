import pytest
from fastapi.testclient import TestClient

from aiops.api import create_app


@pytest.fixture()
def client(trained, tmp_path):
    app = create_app(str(trained["art"] / "best_model.joblib"), str(tmp_path / "req.jsonl"))
    return TestClient(app)


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_health_unavailable_without_model(tmp_path):
    c = TestClient(create_app(str(tmp_path / "absent.joblib"), str(tmp_path / "l.jsonl")))
    assert c.get("/health").status_code == 503


def test_predict_valid(client):
    r = client.post("/predict", json={"counts": [3.0] * 29})
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["anomaly_score"] <= 1.0 and isinstance(body["is_anomaly"], bool)


def test_predict_wrong_length_rejected(client):
    assert client.post("/predict", json={"counts": [1.0, 2.0]}).status_code == 422


def test_predict_negative_rejected(client):
    assert client.post("/predict", json={"counts": [-1.0] + [0.0] * 28}).status_code == 422


def test_metrics_track_requests_and_errors(client):
    client.post("/predict", json={"counts": [3.0] * 29})
    client.post("/predict", json={"counts": [1.0]})
    m = client.get("/metrics").json()
    assert m["n_requests"] == 2 and m["n_errors"] == 1 and m["latency_ms_p95"] >= 0
