import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _bool(name, default):
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _float(name, default):
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int(name, default):
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _database_uri():
    configured = os.environ.get("DATABASE_URL")
    if configured:
        if configured.startswith("sqlite:///") and not configured.startswith("sqlite:////"):
            relative = configured.removeprefix("sqlite:///")
            path = Path(relative)
            if not path.is_absolute():
                path = ROOT / path
            return "sqlite:///" + path.as_posix()
        return configured
    return "sqlite:///" + (ROOT / "instance" / "portal.db").as_posix()


def _grafana_url():
    url = os.environ.get("GRAFANA_BASE_URL", "").strip()
    if url.startswith("https://") or url.startswith("http://"):
        return url
    return ""


def build_config():
    token = (os.environ.get("PROMETHEUS_BEARER_TOKEN") or "").strip() or None
    secure_default = os.environ.get("FLASK_ENV") == "production"
    return {
        "SECRET_KEY": os.environ.get("SECRET_KEY", "dev-only-change-me"),
        "SQLALCHEMY_DATABASE_URI": _database_uri(),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": _bool("SESSION_COOKIE_SECURE", secure_default),
        "PROMETHEUS_BASE_URL": os.environ.get("PROMETHEUS_BASE_URL", "http://127.0.0.1:9090").rstrip("/"),
        "PROMETHEUS_TIMEOUT_SECONDS": _float("PROMETHEUS_TIMEOUT_SECONDS", 3),
        "PROMETHEUS_BEARER_TOKEN": token,
        "PROMETHEUS_VERIFY_SSL": _bool("PROMETHEUS_VERIFY_SSL", True),
        "AUTOMATION_EXECUTOR": os.environ.get("AUTOMATION_EXECUTOR", "mock").strip() or "mock",
        "AUTO_REMEDIATION_ENABLED": _bool("AUTO_REMEDIATION_ENABLED", False),
        "GRAFANA_BASE_URL": _grafana_url(),
        "ALERTMANAGER_WEBHOOK_TOKEN": (os.environ.get("ALERTMANAGER_WEBHOOK_TOKEN") or "").strip() or None,
        "PROBE_TIMEOUT_SECONDS": _float("PROBE_TIMEOUT_SECONDS", 2),
        "JOB_OUTPUT_MAX_CHARS": _int("JOB_OUTPUT_MAX_CHARS", 4000),
        "DEMO_USER_PASSWORD": os.environ.get("DEMO_USER_PASSWORD", ""),
    }
