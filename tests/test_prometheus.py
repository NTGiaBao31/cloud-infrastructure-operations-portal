from unittest.mock import Mock

import requests

from app.services.metrics import collect_metrics
from app.services.prometheus import PrometheusClient, QueryResult, IntegrationStatus


def _client():
    return PrometheusClient("http://prometheus.example", timeout=1, bearer_token="super-secret-token")


def test_query_and_alerts_parse():
    client = _client()
    assert client.session.headers["Authorization"] == "Bearer super-secret-token"
    query_response = Mock(status_code=200)
    query_response.json.return_value = {
        "status": "success",
        "data": {"resultType": "vector", "result": [{"value": [1, "99.5"]}]},
    }
    range_response = Mock(status_code=200)
    range_response.json.return_value = {
        "status": "success",
        "data": {"resultType": "matrix", "result": [{"values": [[1, "1"]]}]},
    }
    alert_response = Mock(status_code=200)
    alert_response.json.return_value = {
        "status": "success",
        "data": {
            "alerts": [
                {
                    "labels": {"alertname": "service_down", "severity": "critical", "instance": "web-01.local:9100"},
                    "annotations": {"summary": "down", "description": "nginx"},
                    "state": "firing",
                    "activeAt": "2026-10-06T01:02:03Z",
                }
            ]
        },
    }
    client.session.get = Mock(side_effect=[query_response, range_response, alert_response])
    instant = client.instant_query("avg(up)")
    assert instant.available is True
    assert instant.data["result"][0]["value"][1] == "99.5"
    from datetime import datetime, timezone

    ranged = client.range_query(
        "avg(up)",
        datetime(2026, 10, 6, tzinfo=timezone.utc),
        datetime(2026, 10, 6, 1, tzinfo=timezone.utc),
        "15s",
    )
    assert ranged.available is True
    alerts = client.list_alerts()
    assert alerts[0].alert_name == "service_down"
    assert alerts[0].severity == "critical"
    assert alerts[0].instance == "web-01.local:9100"
    assert "super-secret-token" not in alerts[0].summary


def test_timeout_and_malformed_are_unavailable():
    client = _client()
    client.session.get = Mock(side_effect=requests.Timeout())
    timed_out = client.instant_query("avg(up)")
    assert timed_out.available is False
    assert timed_out.message == "timeout"
    assert "super-secret-token" not in timed_out.message

    malformed = Mock(status_code=200)
    malformed.json.side_effect = ValueError("bad")
    client.session.get = Mock(return_value=malformed)
    result = client.instant_query("avg(up)")
    assert result.available is False
    assert result.message == "malformed response"

    health = Mock(status_code=200, text="ok")
    client.session.get = Mock(return_value=health)
    assert client.health().available is True


def test_dashboard_metrics_show_na_for_bad_payload(app, monkeypatch):
    class FakeClient:
        def health(self):
            return IntegrationStatus(True, "ok")

        def instant_query(self, query, time=None):
            return QueryResult(False, message="malformed response")

    monkeypatch.setattr("app.services.metrics.client_from_app", lambda: FakeClient())
    with app.app_context():
        values, hosts, status = collect_metrics(probe_http=lambda url, timeout=2: False, probe_tcp=lambda host, port, timeout=2: False)
    assert status.available is True
    assert values == {"availability": "N/A", "cpu": "N/A", "memory": "N/A", "disk": "N/A"}
    assert hosts[0]["cpu"] == "N/A"
    assert hosts[0]["name"] == "WEB01"
    assert hosts[0]["status"] == "Unreachable"
    assert hosts[0]["exporter"] == "DOWN"


def test_host_status_is_degraded_when_only_the_service_is_down(app, monkeypatch):
    class FakeClient:
        def health(self):
            return IntegrationStatus(True, "ok")

        def instant_query(self, query, time=None):
            if query.startswith("up{"):
                return QueryResult(True, data={"result": [{"value": [1, "1"]}]})
            if "node_boot_time" in query:
                return QueryResult(True, data={"result": [{"value": [1, "90000"]}]})
            return QueryResult(True, data={"result": [{"value": [1, "12.5"]}]})

    monkeypatch.setattr("app.services.metrics.client_from_app", lambda: FakeClient())
    with app.app_context():
        _values, hosts, status = collect_metrics(
            probe_http=lambda url, timeout=2: False,
            probe_tcp=lambda host, port, timeout=2: True,
        )
    by_name = {host["name"]: host for host in hosts}
    assert status.available is True
    assert by_name["WEB01"]["status"] == "Degraded"
    assert by_name["WEB01"]["exporter"] == "UP"
    assert by_name["WEB01"]["services"][0]["status"] == "DOWN"
    assert by_name["WEB01"]["cpu"] == "12.5%"
    assert by_name["WIN01"]["status"] == "Healthy"
    assert by_name["MON01"]["exporter_label"] == "Node Exporter :9100"
    assert by_name["MON01"]["instance"] == "192.168.10.10:9100"
    assert by_name["MON01"]["cpu"] == "12.5%"
    assert [service["name"] for service in by_name["MON01"]["services"]] == [
        "Prometheus :9090",
        "Alertmanager :9093",
        "Grafana :3000",
    ]
    assert by_name["MON01"]["status"] == "Degraded"
