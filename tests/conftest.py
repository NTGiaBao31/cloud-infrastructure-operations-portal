import re

import pytest
from flask_migrate import upgrade

from app import create_app
from app.extensions import db


@pytest.fixture(autouse=True)
def fast_probes(monkeypatch):
    monkeypatch.setattr("app.services.metrics.http_probe", lambda url, timeout=2: False)
    monkeypatch.setattr("app.services.metrics.tcp_probe", lambda host, port, timeout=2: False)


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_USER_PASSWORD", "demo-pass")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    database = tmp_path / "portal.db"
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + database.as_posix(),
            "SECRET_KEY": "test-secret",
            "DEMO_USER_PASSWORD": "demo-pass",
            "PROMETHEUS_BASE_URL": "http://127.0.0.1:9",
            "PROMETHEUS_TIMEOUT_SECONDS": 1,
            "PROMETHEUS_BEARER_TOKEN": None,
            "PROMETHEUS_VERIFY_SSL": True,
            "AUTOMATION_EXECUTOR": "mock",
            "AUTO_REMEDIATION_ENABLED": False,
            "GRAFANA_BASE_URL": "",
            "ALERTMANAGER_WEBHOOK_TOKEN": None,
            "PROBE_TIMEOUT_SECONDS": 0.2,
            "JOB_OUTPUT_MAX_CHARS": 4000,
            "SESSION_COOKIE_SECURE": False,
        }
    )
    with application.app_context():
        upgrade()
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seeded(app):
    from app.seed import seed_demo_data

    with app.app_context():
        seed_demo_data()
    return app


def csrf_from(response):
    text = response.get_data(as_text=True)
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', text)
    if match is None:
        match = re.search(r'value="([^"]+)"[^>]*name="csrf_token"', text)
    assert match, "CSRF token missing"
    return match.group(1)


def login(client, username, password="demo-pass"):
    page = client.get("/login")
    token = csrf_from(page)
    return client.post(
        "/login",
        data={"username": username, "password": password, "csrf_token": token, "submit": "Sign in"},
        follow_redirects=True,
    )


def post_csrf(client, url, data, page="/dashboard"):
    token = csrf_from(client.get(page))
    payload = dict(data)
    payload["csrf_token"] = token
    return client.post(url, data=payload)
