from flask import Blueprint, jsonify, request

from app.extensions import csrf
from app.services.alert_webhook import ingest_alertmanager_payload, webhook_token_is_valid

bp = Blueprint("webhooks", __name__)


@bp.post("/api/alerts/webhook")
@csrf.exempt
def alertmanager():
    token = request.headers.get("X-Webhook-Token") or ""
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not webhook_token_is_valid(token):
        return jsonify({"status": "error", "message": "unauthorized"}), 401
    payload = request.get_json(silent=True)
    result = ingest_alertmanager_payload(payload)
    if not result.accepted:
        return jsonify({"status": "error", "message": result.message}), 400
    return jsonify({"status": "ok", "message": result.message}), 202
