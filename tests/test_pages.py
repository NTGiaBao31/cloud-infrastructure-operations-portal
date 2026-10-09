from sqlalchemy import select

from app.extensions import db
from app.models import Server
from tests.conftest import login


def test_healthz_is_public(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json["database"] == "ok"


def test_pages_render_without_prometheus(seeded, client):
    login(client, "viewer")
    with seeded.app_context():
        server_id = db.session.scalar(select(Server.id).where(Server.name == "web-01"))
    paths = ["/dashboard", "/servers/", "/alerts/", "/automation/", "/audit/", f"/servers/{server_id}"]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, path
    dashboard = client.get("/dashboard")
    assert b"N/A" in dashboard.data
    assert b"Grafana is not configured." in dashboard.data
