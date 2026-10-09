import json
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.extensions import db
from app.models import Alert, AuditLog, AutomationJob
from app.services.alert_sync import sync_alerts
from app.services.prometheus import PrometheusAlert
from app.services.remediation import maybe_remediate
from tests.test_alert_sync import FakePrometheus


def _alert(name, fingerprint):
    return PrometheusAlert(
        fingerprint=fingerprint,
        alert_name=name,
        severity="critical",
        category="availability",
        summary=name,
        description="detail",
        state="firing",
        starts_at=datetime(2026, 10, 6, 4, tzinfo=timezone.utc),
        labels={"instance": "web-01.local", "alertname": name},
        instance="web-01.local",
    )


def test_remediation_creates_one_job_and_audit(seeded):
    seeded.config["AUTO_REMEDIATION_ENABLED"] = True
    with seeded.app_context():
        before_jobs = db.session.scalar(select(func.count()).select_from(AutomationJob))
        first = sync_alerts(FakePrometheus([_alert("service_down", "fp-remediate")]))
        assert first.remediated == 1
        second = sync_alerts(FakePrometheus([_alert("service_down", "fp-remediate")]))
        assert second.remediated == 0
        alert = db.session.scalar(select(Alert).where(Alert.fingerprint == "fp-remediate"))
        jobs = db.session.scalars(select(AutomationJob).where(AutomationJob.alert_id == alert.id)).all()
        assert len(jobs) == 1
        assert jobs[0].action_key == "restart_service"
        assert jobs[0].trigger_source == "remediation"
        assert jobs[0].status == "succeeded"
        audits = db.session.scalars(select(AuditLog).where(AuditLog.resource_id == str(alert.id))).all()
        actions = {entry.action for entry in audits}
        assert "remediation.request" in actions
        assert db.session.scalar(select(func.count()).select_from(AutomationJob)) == before_jobs + 1


def test_disk_cleanup_is_dry_run_and_failed_job_can_retry(seeded):
    seeded.config["AUTO_REMEDIATION_ENABLED"] = True
    with seeded.app_context():
        sync_alerts(FakePrometheus([_alert("disk_high", "fp-disk")]))
        alert = db.session.scalar(select(Alert).where(Alert.fingerprint == "fp-disk"))
        job = db.session.scalar(select(AutomationJob).where(AutomationJob.alert_id == alert.id))
        assert json.loads(job.parameters_json)["dry_run"] == "true"
        job.status = "failed"
        db.session.commit()
        retried = maybe_remediate(alert)
        assert retried is not None
        assert retried.id != job.id
        assert maybe_remediate(alert) is None


def test_unmatched_alert_is_stored_without_a_job(seeded):
    seeded.config["AUTO_REMEDIATION_ENABLED"] = True
    with seeded.app_context():
        before = db.session.scalar(select(func.count()).select_from(AutomationJob))
        sync_alerts(FakePrometheus([_alert("latency_high", "fp-latency")]))
        alert = db.session.scalar(select(Alert).where(Alert.fingerprint == "fp-latency"))
        assert alert is not None
        assert maybe_remediate(alert) is None
        assert db.session.scalar(select(func.count()).select_from(AutomationJob)) == before
