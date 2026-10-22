from dataclasses import dataclass

from flask import current_app

from app.extensions import db
from app.services.alert_sync import upsert_remote
from app.services.audit import record
from app.services.prometheus import PrometheusAlert, fingerprint_for, parse_time
from app.services.remediation import maybe_remediate


@dataclass
class WebhookResult:
    accepted: bool
    message: str
    created: int = 0
    updated: int = 0
    resolved: int = 0
    reopened: int = 0
    remediated: int = 0


def ingest_alertmanager_payload(payload):
    if not isinstance(payload, dict):
        return WebhookResult(False, "payload must be an object")
    alerts = payload.get("alerts")
    if not isinstance(alerts, list):
        return WebhookResult(False, "alerts must be a list")
    created = updated = resolved = reopened = remediated = 0
    for item in alerts:
        if not isinstance(item, dict):
            continue
        remote = _from_alertmanager(item)
        outcome, alert, opened = upsert_remote(remote, source="alertmanager")
        if outcome == "created":
            created += 1
            record(
                "alert.received",
                "alert",
                alert.id,
                {"fingerprint": alert.fingerprint, "alert_name": alert.alert_name, "status": alert.status},
            )
        elif outcome == "updated":
            updated += 1
        elif outcome == "resolved":
            resolved += 1
            record(
                "alert.resolved",
                "alert",
                alert.id,
                {"fingerprint": alert.fingerprint, "alert_name": alert.alert_name},
            )
        elif outcome == "reopened":
            reopened += 1
            record(
                "alert.received",
                "alert",
                alert.id,
                {"fingerprint": alert.fingerprint, "alert_name": alert.alert_name, "status": "firing"},
            )
        if opened and alert is not None:
            job = maybe_remediate(alert)
            if job is not None:
                remediated += 1
                record(
                    "automation.trigger",
                    "automation_job",
                    job.id,
                    {"alert_id": alert.id, "action_key": job.action_key},
                )
    db.session.commit()
    return WebhookResult(
        True,
        f"created={created} updated={updated} resolved={resolved} reopened={reopened} remediated={remediated}",
        created=created,
        updated=updated,
        resolved=resolved,
        reopened=reopened,
        remediated=remediated,
    )


def webhook_token_is_valid(header_token):
    expected = current_app.config.get("ALERTMANAGER_WEBHOOK_TOKEN")
    if not expected:
        return True
    return bool(header_token) and header_token == expected


def _from_alertmanager(item):
    labels = item.get("labels") if isinstance(item.get("labels"), dict) else {}
    annotations = item.get("annotations") if isinstance(item.get("annotations"), dict) else {}
    alert_name = str(labels.get("alertname") or "unknown")[:120]
    severity = str(labels.get("severity") or "warning").lower()
    if severity not in {"critical", "warning", "info"}:
        severity = "critical" if alert_name in {"InstanceDown", "service_down"} else "warning"
    instance = labels.get("instance") or labels.get("hostname")
    status = str(item.get("status") or "firing").lower()
    state = "resolved" if status == "resolved" else "firing"
    fingerprint = str(item.get("fingerprint") or fingerprint_for(labels))[:128]
    return PrometheusAlert(
        fingerprint=fingerprint,
        alert_name=alert_name,
        severity=severity,
        category=labels.get("job") or labels.get("category"),
        summary=str(annotations.get("summary") or alert_name)[:255],
        description=str(annotations.get("description") or ""),
        state=state,
        starts_at=parse_time(item.get("startsAt")),
        ends_at=parse_time(item.get("endsAt")),
        labels=labels,
        annotations=annotations,
        instance=None if instance is None else str(instance),
    )
