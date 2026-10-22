from flask import current_app
from sqlalchemy import select

from app.extensions import db
from app.models import AutomationJob, Server
from app.services.audit import record
from app.services.automation import AutomationRejected, dispatch, enqueue_job

POLICIES = {
    "service_down": "restart_service",
    "container_down": "restart_container",
    "disk_high": "disk_cleanup",
    "InstanceDown": "restart_service",
}


def default_parameters(action_key):
    if action_key == "restart_service":
        return {"service_name": "app"}
    if action_key == "restart_container":
        return {"container_name": "app"}
    return {"path": "var-log"}


def maybe_remediate(alert):
    if not current_app.config.get("AUTO_REMEDIATION_ENABLED"):
        return None
    if alert.status != "firing" or alert.alert_name not in POLICIES:
        return None
    if alert.server_id is None:
        return None
    server = db.session.get(Server, alert.server_id)
    if server is None or not server.is_active:
        return None
    action_key = POLICIES[alert.alert_name]
    existing = db.session.scalar(
        select(AutomationJob.id).where(
            AutomationJob.alert_id == alert.id,
            AutomationJob.action_key == action_key,
            AutomationJob.status.in_(("queued", "running", "succeeded")),
        )
    )
    if existing is not None:
        return None
    record(
        "remediation.request",
        "alert",
        alert.id,
        {"action_key": action_key, "alert_id": alert.id},
    )
    try:
        job = enqueue_job(
            server_id=server.id,
            action_key=action_key,
            parameters=default_parameters(action_key),
            trigger_source="remediation",
            requested_by=None,
            alert_id=alert.id,
        )
        return dispatch(job.id, actor=None)
    except AutomationRejected:
        current_app.logger.info("Remediation skipped")
        return None
