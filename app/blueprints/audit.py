from flask import Blueprint, render_template
from sqlalchemy import select

from app.extensions import db
from app.models import AuditLog

bp = Blueprint("audit", __name__, url_prefix="/audit")


@bp.get("/")
def index():
    entries = db.session.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)).all()
    return render_template("audit/list.html", entries=entries)
