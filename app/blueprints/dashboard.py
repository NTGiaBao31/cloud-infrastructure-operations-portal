from flask import Blueprint, render_template
from sqlalchemy import func, select

from app.extensions import db
from app.models import Alert, AutomationJob, Server
from app.services.metrics import collect_metrics

bp = Blueprint("dashboard", __name__)


@bp.get("/dashboard")
def index():
    status_rows = db.session.execute(select(Server.status, func.count()).group_by(Server.status)).all()
    status_counts = {status: count for status, count in status_rows}
    severity_rows = db.session.execute(
        select(Alert.severity, func.count())
        .where(Alert.status.in_(("firing", "acknowledged")))
        .group_by(Alert.severity)
    ).all()
    severity_counts = {severity: count for severity, count in severity_rows}
    recent_jobs = db.session.scalars(select(AutomationJob).order_by(AutomationJob.created_at.desc()).limit(5)).all()
    metrics, prometheus = collect_metrics()
    return render_template(
        "dashboard.html",
        status_counts=status_counts,
        severity_counts=severity_counts,
        recent_jobs=recent_jobs,
        metrics=metrics,
        prometheus_available=prometheus.available,
        server_total=sum(status_counts.values()),
        open_alerts=sum(severity_counts.values()),
    )
