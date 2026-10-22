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
    assert b"Monitoring backend" in dashboard.data
    assert b"Host status" in dashboard.data
    assert b"Node Exporter :9100" in dashboard.data
    assert b"Windows Exporter :9182" in dashboard.data
    assert b"WinRM :5985" in dashboard.data
    assert b"Ask an administrator if you need Grafana access." in dashboard.data
    snapshot = client.get("/dashboard/snapshot")
    assert snapshot.status_code == 200
    body = snapshot.get_json()
    assert "hosts" in body
    assert "services" in body
    assert body["kpis"]["servers"] == 4
    assert "issues" in body
    events = client.get("/dashboard/events/WEB01")
    assert events.status_code == 200
    assert events.get_json()["host"]["name"] == "WEB01"
    for path in ["/servers/", "/alerts/", "/audit/"]:
        assert client.get(path).status_code == 200
