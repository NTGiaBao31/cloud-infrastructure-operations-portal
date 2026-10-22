from sqlalchemy import func, select

from app.extensions import db
from app.models import Alert, AuditLog


def _payload(status, instance="192.168.10.11:9100", fingerprint="am-web01-down"):
    ends = "2026-10-22T10:05:00.000Z" if status == "resolved" else "0001-01-01T00:00:00Z"
    return {
        "version": "4",
        "status": status,
        "alerts": [
            {
                "status": status,
                "labels": {
                    "alertname": "InstanceDown",
                    "instance": instance,
                    "job": "node",
                    "severity": "critical",
                },
                "annotations": {"summary": "WEB01 exporter is down", "description": "up == 0"},
                "startsAt": "2026-10-22T10:00:00.000Z",
                "endsAt": ends,
                "fingerprint": fingerprint,
            }
        ],
    }


def test_webhook_is_public_and_maps_web01(seeded, client):
    response = client.post("/api/alerts/webhook", json=_payload("firing"))
    assert response.status_code == 202
    with seeded.app_context():
        alert = db.session.scalar(select(Alert).where(Alert.fingerprint == "am-web01-down"))
        assert alert is not None
        assert alert.alert_name == "InstanceDown"
        assert alert.status == "firing"
        assert alert.server.name == "WEB01"
        assert alert.source == "alertmanager"
        received = db.session.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.action == "alert.received")
        )
        assert received >= 1


def test_webhook_resolves_without_duplicate(seeded, client):
    client.post("/api/alerts/webhook", json=_payload("firing"))
    again = client.post("/api/alerts/webhook", json=_payload("resolved"))
    assert again.status_code == 202
    with seeded.app_context():
        count = db.session.scalar(select(func.count()).select_from(Alert).where(Alert.fingerprint == "am-web01-down"))
        alert = db.session.scalar(select(Alert).where(Alert.fingerprint == "am-web01-down"))
        assert count == 1
        assert alert.status == "resolved"
        assert alert.resolved_at is not None
        resolved = db.session.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.action == "alert.resolved")
        )
        assert resolved >= 1


def test_webhook_rejects_bad_payload(client):
    response = client.post("/api/alerts/webhook", json=["not", "an", "object"])
    assert response.status_code == 400
