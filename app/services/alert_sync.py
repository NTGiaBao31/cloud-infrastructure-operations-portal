from dataclasses import dataclass

from sqlalchemy import select

from app.extensions import db
from app.models import Alert, utcnow
from app.services.audit import record
from app.services.inventory import match_server
from app.services.prometheus import PrometheusUnavailable, client_from_app
from app.services.remediation import maybe_remediate


@dataclass
class SyncResult:
    available: bool
    message: str
    created: int = 0
    updated: int = 0
    resolved: int = 0
    reopened: int = 0
    remediated: int = 0


def sync_alerts(client=None):
    prometheus = client or client_from_app()
    try:
        remote_alerts = prometheus.list_alerts()
    except PrometheusUnavailable as exc:
        record("prometheus.unavailable", "prometheus", None, {"message": str(exc), "source": "sync"})
        return SyncResult(False, str(exc))

    seen = set()
    created = updated = resolved = reopened = remediated = 0
    for remote in remote_alerts:
        seen.add(remote.fingerprint)
        outcome, alert, opened = upsert_remote(remote, source="prometheus")
        if outcome == "created":
            created += 1
        elif outcome == "updated":
            updated += 1
        elif outcome == "resolved":
            resolved += 1
        elif outcome == "reopened":
            reopened += 1
        if opened and alert is not None:
            job = maybe_remediate(alert)
            if job is not None:
                remediated += 1

    resolved += _resolve_missing(seen)
    db.session.commit()
    return SyncResult(
        True,
        f"created={created} updated={updated} resolved={resolved} reopened={reopened} remediated={remediated}",
        created=created,
        updated=updated,
        resolved=resolved,
        reopened=reopened,
        remediated=remediated,
    )


def upsert_remote(remote, source="prometheus"):
    matches = list(
        db.session.scalars(select(Alert).where(Alert.fingerprint == remote.fingerprint).order_by(Alert.id.desc()))
    )
    status = _status_for(remote.state)
    server = match_server(remote.instance, labels=remote.labels or {})
    if not matches:
        alert = Alert(
            server_id=server.id if server else None,
            fingerprint=remote.fingerprint,
            alert_name=remote.alert_name,
            category=remote.category,
            source=source,
            severity=remote.severity,
            status=status,
            summary=remote.summary,
            description=remote.description,
            starts_at=remote.starts_at or utcnow(),
            resolved_at=(getattr(remote, "ends_at", None) or utcnow()) if status == "resolved" else None,
            created_at=utcnow(),
        )
        db.session.add(alert)
        db.session.flush()
        return "created", alert, status == "firing"
    alert = matches[0]
    opened = False
    outcome = "updated"
    if alert.status == "resolved" and status == "firing" and _is_newer(remote.starts_at, alert.starts_at):
        alert.status = "firing"
        alert.acknowledged_by = None
        alert.acknowledged_at = None
        alert.resolved_at = None
        alert.starts_at = remote.starts_at or utcnow()
        opened = True
        outcome = "reopened"
    elif alert.status == "resolved" and status == "firing":
        outcome = "updated"
    elif status == "resolved" and alert.status != "resolved":
        alert.status = "resolved"
        alert.resolved_at = getattr(remote, "ends_at", None) or alert.resolved_at or utcnow()
        outcome = "resolved"
    elif alert.status == "acknowledged" and status == "firing":
        outcome = "updated"
    else:
        if alert.status != status:
            outcome = "resolved" if status == "resolved" else "updated"
        alert.status = status
        if status == "resolved":
            alert.resolved_at = getattr(remote, "ends_at", None) or alert.resolved_at or utcnow()
    alert.alert_name = remote.alert_name
    alert.category = remote.category
    alert.source = source
    alert.severity = remote.severity
    alert.summary = remote.summary
    alert.description = remote.description
    alert.server_id = server.id if server else alert.server_id
    db.session.flush()
    return outcome, alert, opened


def _resolve_missing(seen):
    rows = db.session.scalars(
        select(Alert).where(
            Alert.source == "prometheus",
            Alert.status.in_(("firing", "acknowledged")),
        )
    ).all()
    count = 0
    for alert in rows:
        if alert.fingerprint not in seen:
            alert.status = "resolved"
            alert.resolved_at = alert.resolved_at or utcnow()
            count += 1
    return count


def _status_for(state):
    if state in {"inactive", "resolved"}:
        return "resolved"
    return "firing"


def _is_newer(remote_starts, existing_starts):
    if remote_starts is None:
        return True
    if existing_starts is None:
        return True
    return _as_utc(remote_starts) > _as_utc(existing_starts)


def _as_utc(value):
    from datetime import timezone

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

