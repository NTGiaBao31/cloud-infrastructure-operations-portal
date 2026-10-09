from dataclasses import dataclass

from sqlalchemy import select

from app.extensions import db
from app.models import Alert, Server, utcnow
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
        return SyncResult(False, str(exc))

    seen = set()
    created = updated = resolved = reopened = remediated = 0
    for remote in remote_alerts:
        seen.add(remote.fingerprint)
        outcome, alert, opened = _upsert(remote)
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


def _upsert(remote):
    matches = list(
        db.session.scalars(select(Alert).where(Alert.fingerprint == remote.fingerprint).order_by(Alert.id.desc()))
    )
    status = _status_for(remote.state)
    server = _match_server(remote)
    if not matches:
        alert = Alert(
            server_id=server.id if server else None,
            fingerprint=remote.fingerprint,
            alert_name=remote.alert_name,
            category=remote.category,
            source="prometheus",
            severity=remote.severity,
            status=status,
            summary=remote.summary,
            description=remote.description,
            starts_at=remote.starts_at or utcnow(),
            resolved_at=utcnow() if status == "resolved" else None,
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
        alert.resolved_at = alert.resolved_at or utcnow()
        outcome = "resolved"
    elif alert.status == "acknowledged" and status == "firing":
        outcome = "updated"
    else:
        if alert.status != status:
            outcome = "resolved" if status == "resolved" else "updated"
        alert.status = status
        if status == "resolved":
            alert.resolved_at = alert.resolved_at or utcnow()
    alert.alert_name = remote.alert_name
    alert.category = remote.category
    alert.source = "prometheus"
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


def _match_server(remote):
    candidates = []
    labels = remote.labels or {}
    for key in ("monitoring_target", "instance", "hostname", "host", "ip"):
        value = labels.get(key)
        if value:
            candidates.append(str(value))
    if remote.instance and remote.instance not in candidates:
        candidates.append(remote.instance)
    expanded = []
    for candidate in candidates:
        expanded.append(candidate)
        if ":" in candidate:
            expanded.append(candidate.split(":", 1)[0])
    servers = list(db.session.scalars(select(Server)))
    by_target = {server.monitoring_target: server for server in servers if server.monitoring_target}
    by_host = {server.hostname: server for server in servers}
    by_ip = {server.ip_address: server for server in servers}
    for candidate in expanded:
        if candidate in by_target:
            return by_target[candidate]
    for candidate in expanded:
        if candidate in by_host:
            return by_host[candidate]
    for candidate in expanded:
        if candidate in by_ip:
            return by_ip[candidate]
    return None


def _status_for(state):
    if state == "inactive":
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

