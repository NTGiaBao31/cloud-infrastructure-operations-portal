from sqlalchemy import select

from app.extensions import db
from app.models import Alert, Server, User
from tests.conftest import login, post_csrf


def test_login_logout_and_inactive_user(seeded, client):
    for username in ("admin", "operator", "viewer"):
        response = login(client, username)
        assert response.status_code == 200
        assert b"Dashboard" in response.data
        page = client.get("/dashboard")
        from tests.conftest import csrf_from

        client.post("/logout", data={"csrf_token": csrf_from(page)})
    with seeded.app_context():
        viewer = db.session.scalar(select(User).where(User.username == "viewer"))
        viewer.is_active = False
        db.session.commit()
    response = login(client, "viewer")
    assert b"Account is inactive." in response.data


def test_viewer_mutations_are_forbidden(seeded, client):
    login(client, "viewer")
    with seeded.app_context():
        alert_id = db.session.scalar(select(Alert.id).where(Alert.status == "firing"))
        server_id = db.session.scalar(select(Server.id).where(Server.name == "web-01"))
    assert post_csrf(client, f"/alerts/{alert_id}/acknowledge", {}).status_code == 403
    assert post_csrf(
        client,
        "/automation/jobs",
        {"server_id": server_id, "action_key": "restart_service", "service_name": "nginx", "simulate": "success"},
    ).status_code == 403
    assert post_csrf(client, f"/servers/{server_id}/edit", {"name": "web-01"}).status_code == 403


def test_operator_can_acknowledge_and_run_but_not_edit_inventory(seeded, client):
    login(client, "operator")
    with seeded.app_context():
        alert_id = db.session.scalar(select(Alert.id).where(Alert.fingerprint == "demo-fp-service-down-web"))
        server_id = db.session.scalar(select(Server.id).where(Server.name == "web-01"))
    acknowledged = post_csrf(client, f"/alerts/{alert_id}/acknowledge", {}, page="/alerts/")
    assert acknowledged.status_code == 302
    denied = post_csrf(client, f"/servers/{server_id}/edit", {"name": "web-01"}, page="/servers/")
    assert denied.status_code == 403
    created = post_csrf(
        client,
        "/automation/jobs",
        {
            "server_id": str(server_id),
            "action_key": "restart_service",
            "service_name": "nginx",
            "container_name": "",
            "path": "",
            "simulate": "success",
            "submit": "Run action",
        },
        page="/automation/",
    )
    assert created.status_code == 302
    with seeded.app_context():
        db.session.expire_all()
        alert = db.session.get(Alert, alert_id)
        assert alert.status == "acknowledged"


def test_admin_can_create_server(seeded, client):
    login(client, "admin")
    response = post_csrf(
        client,
        "/servers/new",
        {
            "name": "cache-01",
            "hostname": "cache-01.local",
            "ip_address": "10.0.0.40",
            "environment": "prod",
            "os_type": "linux",
            "status": "online",
            "monitoring_target": "",
            "automation_group": "linux_web",
            "azure_resource_id": "",
            "submit": "Save server",
        },
        page="/servers/new",
    )
    assert response.status_code == 302
    with seeded.app_context():
        server = db.session.scalar(select(Server).where(Server.name == "cache-01"))
        assert server is not None
        assert server.is_active is True
