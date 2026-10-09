import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

import requests


class PrometheusUnavailable(Exception):
    pass


@dataclass
class IntegrationStatus:
    available: bool
    message: str = ""


@dataclass
class QueryResult:
    available: bool
    data: dict | None = None
    message: str = ""


@dataclass
class PrometheusAlert:
    fingerprint: str
    alert_name: str
    severity: str
    category: str | None
    summary: str
    description: str
    state: str
    starts_at: datetime | None
    labels: dict = field(default_factory=dict)
    annotations: dict = field(default_factory=dict)
    instance: str | None = None


class PrometheusClient:
    """HTTP adapter for Prometheus. Tokens stay in memory on this session."""

    def __init__(self, base_url, timeout=3, bearer_token=None, verify_ssl=True):
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = verify_ssl
        if bearer_token:
            self.session.headers["Authorization"] = f"Bearer {bearer_token}"

    def health(self):
        try:
            self._get("/-/healthy")
        except PrometheusUnavailable as exc:
            return IntegrationStatus(False, str(exc))
        return IntegrationStatus(True, "ok")

    def instant_query(self, query, time=None):
        params = {"query": query}
        if time is not None:
            params["time"] = str(_unix(time))
        return self._query("/api/v1/query", params)

    def range_query(self, query, start, end, step):
        params = {
            "query": query,
            "start": str(_unix(start)),
            "end": str(_unix(end)),
            "step": step,
        }
        return self._query("/api/v1/query_range", params)

    def list_alerts(self):
        payload = self._get("/api/v1/alerts")
        if not isinstance(payload, dict) or payload.get("status") != "success":
            raise PrometheusUnavailable("malformed response")
        data = payload.get("data")
        alerts = data.get("alerts") if isinstance(data, dict) else None
        if not isinstance(alerts, list):
            raise PrometheusUnavailable("malformed response")
        parsed = []
        for item in alerts:
            if isinstance(item, dict):
                parsed.append(_parse_alert(item))
        return parsed

    def _query(self, path, params):
        try:
            payload = self._get(path, params=params)
        except PrometheusUnavailable as exc:
            return QueryResult(False, message=str(exc))
        if not isinstance(payload, dict) or payload.get("status") != "success":
            return QueryResult(False, message="malformed response")
        data = payload.get("data")
        if not isinstance(data, dict):
            return QueryResult(False, message="malformed response")
        return QueryResult(True, data=data, message="ok")

    def _get(self, path, params=None):
        url = f"{self.base_url}{path}"
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
        except requests.Timeout:
            raise PrometheusUnavailable("timeout") from None
        except requests.ConnectionError:
            raise PrometheusUnavailable("connection error") from None
        except requests.RequestException:
            raise PrometheusUnavailable("request failed") from None
        if response.status_code != 200:
            raise PrometheusUnavailable(f"http {response.status_code}")
        if path == "/-/healthy":
            return response
        try:
            return response.json()
        except ValueError:
            raise PrometheusUnavailable("malformed response") from None


def client_from_app():
    from flask import current_app

    config = current_app.config
    return PrometheusClient(
        base_url=config["PROMETHEUS_BASE_URL"],
        timeout=config["PROMETHEUS_TIMEOUT_SECONDS"],
        bearer_token=config.get("PROMETHEUS_BEARER_TOKEN"),
        verify_ssl=config["PROMETHEUS_VERIFY_SSL"],
    )


def _unix(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp())


def fingerprint_for(labels):
    raw = json.dumps(labels, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def parse_time(value):
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_alert(item):
    labels = item.get("labels") if isinstance(item.get("labels"), dict) else {}
    annotations = item.get("annotations") if isinstance(item.get("annotations"), dict) else {}
    alert_name = str(labels.get("alertname") or item.get("alertname") or "unknown")[:120]
    severity = str(labels.get("severity") or "warning").lower()
    if severity not in {"critical", "warning", "info"}:
        severity = "warning"
    category = labels.get("category") or labels.get("alertgroup")
    instance = labels.get("instance") or labels.get("hostname")
    state = str(item.get("state") or "firing").lower()
    if state not in {"firing", "pending", "inactive"}:
        state = "firing"
    return PrometheusAlert(
        fingerprint=str(item.get("fingerprint") or fingerprint_for(labels))[:128],
        alert_name=alert_name,
        severity=severity,
        category=None if category is None else str(category)[:80],
        summary=str(annotations.get("summary") or alert_name)[:255],
        description=str(annotations.get("description") or ""),
        state=state,
        starts_at=parse_time(item.get("activeAt") or item.get("startsAt")),
        labels=labels,
        annotations=annotations,
        instance=None if instance is None else str(instance),
    )
