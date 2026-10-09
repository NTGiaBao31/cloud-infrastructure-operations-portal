import json

from flask import has_request_context, request
from flask_login import current_user

from app.extensions import db
from app.models import AuditLog, utcnow


def record(action, resource_type, resource_id=None, details=None, user_id=None):
    if user_id is None and has_request_context() and current_user.is_authenticated:
        user_id = current_user.id
    payload = json.dumps(details or {}, default=str, sort_keys=True)
    if len(payload) > 4000:
        payload = payload[:4000]
    ip_address = None
    if has_request_context() and request.remote_addr:
        ip_address = request.remote_addr[:45]
    entry = AuditLog(
        user_id=user_id,
        action=action[:80],
        resource_type=resource_type[:40],
        resource_id=None if resource_id is None else str(resource_id)[:64],
        details_json=payload,
        ip_address=ip_address,
        created_at=utcnow(),
    )
    db.session.add(entry)
    db.session.commit()
    return entry
