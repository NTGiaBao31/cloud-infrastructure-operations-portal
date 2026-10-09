from datetime import datetime, timezone

from sqlalchemy import func, select

from app.extensions import db
from app.models import Alert
from app.services.alert_sync import sync_alerts
from app.services.prometheus import PrometheusAlert, PrometheusUnavailable


class FakePrometheus:
    def __init__(self, alerts=None, error=None):
        self.alerts = alerts or []
        self.error = error

    def list_alerts(self):
        if self.error:
            raise PrometheusUnavailable(self.error)
        return self.alerts


def _remote(fingerprint, summary, state, starts_at, name="service_down", severity="critical"):
    return PrometheusAlert(
        fingerprint=fingerprint,
        alert_name=name,
        severity=severity,
        category="availability",
        summary=summary,
        description="detail",
        state=state,
        starts_at=starts_at,
        labels={"instance": "web-01.local", "alertname": name, "severity": severity},
        instance="web-01.local",
    )


def test_sync_updates_resolves_and_reopens(seeded):
    first_start = datetime(2026, 10, 6, 1, tzinfo=timezone.utc)
    with seeded.app_context():
        created = sync_alerts(FakePrometheus([_remote("fp-sync", "first", "firing", first_start)]))
        assert created.created == 1
        alert = db.session.scalar(select(Alert).where(Alert.fingerprint == "fp-sync"))
        assert alert.summary == "first"
        assert alert.server.name == "web-01"
        assert alert.source == "prometheus"

        updated = sync_alerts(FakePrometheus([_remote("fp-sync", "second", "firing", first_start)]))
        db.session.expire_all()
        alert = db.session.scalar(select(Alert).where(Alert.fingerprint == "fp-sync"))
        assert updated.updated == 1
        assert alert.summary == "second"
        assert db.session.scalar(select(func.count()).select_from(Alert).where(Alert.fingerprint == "fp-sync")) == 1

        resolved = sync_alerts(FakePrometheus([]))
        db.session.expire_all()
        alert = db.session.scalar(select(Alert).where(Alert.fingerprint == "fp-sync"))
        assert resolved.resolved == 1
        assert alert.status == "resolved"

        later = datetime(2026, 10, 6, 3, tzinfo=timezone.utc)
        reopened = sync_alerts(FakePrometheus([_remote("fp-sync", "again", "firing", later)]))
        db.session.expire_all()
        alert = db.session.scalar(select(Alert).where(Alert.fingerprint == "fp-sync"))
        assert reopened.reopened == 1
        assert alert.status == "firing"
        assert alert.resolved_at is None
        assert alert.summary == "again"


def test_unavailable_sync_does_not_change_rows(seeded):
    with seeded.app_context():
        before = db.session.scalar(select(func.count()).select_from(Alert))
        result = sync_alerts(FakePrometheus(error="timeout"))
        assert result.available is False
        assert db.session.scalar(select(func.count()).select_from(Alert)) == before
        firing = db.session.scalar(select(Alert).where(Alert.fingerprint == "demo-fp-service-down-web"))
        assert firing.status == "firing"


def test_sync_cli_fails_closed_when_prometheus_is_down(seeded):
    result = seeded.test_cli_runner().invoke(args=["sync-prometheus-alerts"])
    assert result.exit_code != 0
    with seeded.app_context():
        assert db.session.scalar(select(func.count()).select_from(Alert)) == 7
