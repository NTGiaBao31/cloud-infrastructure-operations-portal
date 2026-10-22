from app.services.probes import http_probe, tcp_probe


def test_tcp_probe_rejects_closed_port():
    ok, latency = tcp_probe("127.0.0.1", 1, timeout=0.2)
    assert ok is False
    assert latency is None


def test_http_probe_rejects_unreachable_url():
    ok, latency = http_probe("http://127.0.0.1:1/", timeout=0.2)
    assert ok is False
    assert latency is None
