import numpy as np

from aiops.monitor import RuntimeMetrics, psi


def test_psi_identical_distributions_is_low():
    rng = np.random.default_rng(0)
    a, b = rng.normal(size=5000), rng.normal(size=5000)
    assert psi(a, b) < 0.05


def test_psi_detects_shift():
    rng = np.random.default_rng(0)
    assert psi(rng.normal(size=5000), rng.normal(2, 1, size=5000)) > 0.25


def test_runtime_metrics_snapshot():
    m = RuntimeMetrics()
    for i in range(20):
        m.record(latency_ms=float(i), score=0.1, is_anomaly=False)
    m.record_error()
    s = m.snapshot()
    assert s["n_requests"] == 21 and s["n_errors"] == 1
    assert s["latency_ms_p95"] >= s["latency_ms_mean"]
