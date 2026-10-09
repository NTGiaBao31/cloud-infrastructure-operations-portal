from sqlalchemy import func, select

from app.extensions import db
from app.models import Alert, AuditLog, AutomationJob, Server, User


def _counts():
    return {
        "users": db.session.scalar(select(func.count()).select_from(User)),
        "servers": db.session.scalar(select(func.count()).select_from(Server)),
        "alerts": db.session.scalar(select(func.count()).select_from(Alert)),
        "jobs": db.session.scalar(select(func.count()).select_from(AutomationJob)),
        "audits": db.session.scalar(select(func.count()).select_from(AuditLog)),
    }


def test_seed_is_idempotent_and_updates_natural_keys(app):
    runner = app.test_cli_runner()
    first = runner.invoke(args=["seed-demo"])
    assert first.exit_code == 0
    with app.app_context():
        assert _counts() == {"users": 3, "servers": 6, "alerts": 7, "jobs": 8, "audits": 12}
        server = db.session.scalar(select(Server).where(Server.name == "db-01"))
        server.status = "online"
        db.session.commit()
    second = runner.invoke(args=["seed-demo"])
    assert second.exit_code == 0
    with app.app_context():
        assert _counts() == {"users": 3, "servers": 6, "alerts": 7, "jobs": 8, "audits": 12}
        server = db.session.scalar(select(Server).where(Server.name == "db-01"))
        assert server.status == "warning"
        azure = db.session.scalar(select(Server).where(Server.name == "azure-vm-01"))
        assert azure.azure_resource_id
        roles = {row.username: row.role for row in db.session.scalars(select(User))}
        assert roles == {"admin": "admin", "operator": "operator", "viewer": "viewer"}


def test_seed_requires_password(app):
    app.config["DEMO_USER_PASSWORD"] = ""
    result = app.test_cli_runner().invoke(args=["seed-demo"])
    assert result.exit_code != 0
    with app.app_context():
        assert _counts()["users"] == 0
