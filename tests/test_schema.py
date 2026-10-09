import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import AuditLog, User, utcnow


def test_migration_creates_tables_constraints_and_indexes(app):
    with app.app_context():
        tables = {row[0] for row in db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
        assert {"users", "servers", "alerts", "automation_jobs", "audit_logs"} <= tables
        assert db.session.execute(text("PRAGMA foreign_keys")).scalar() == 1
        indexes = {row[0] for row in db.session.execute(text("SELECT name FROM sqlite_master WHERE type='index'"))}
        expected = [
            "ix_servers_status",
            "ix_servers_environment",
            "ix_servers_os_type",
            "ix_alerts_fingerprint",
            "ix_alerts_status",
            "ix_alerts_severity",
            "ix_alerts_server_id",
            "ix_automation_jobs_status",
            "ix_automation_jobs_server_id",
            "ix_automation_jobs_alert_id",
            "ix_automation_jobs_created_at",
            "ix_audit_logs_user_id",
            "ix_audit_logs_action",
            "ix_audit_logs_resource_type",
            "ix_audit_logs_created_at",
        ]
        missing = [name for name in expected if name not in indexes]
        assert missing == []
        for table in ("alerts", "automation_jobs", "audit_logs"):
            sql = db.session.execute(text("SELECT sql FROM sqlite_master WHERE name=:name"), {"name": table}).scalar()
            assert "ON DELETE SET NULL" in sql.upper()
        with pytest.raises(IntegrityError):
            db.session.execute(
                text(
                    "INSERT INTO users (username, password_hash, role, is_active, created_at) "
                    "VALUES ('bad', 'x', 'root', 1, '2026-01-01T00:00:00')"
                )
            )
            db.session.commit()
        db.session.rollback()


def test_user_delete_nulls_audit_user(app):
    with app.app_context():
        user = User(username="temp-user", role="viewer", password_hash="x", is_active=True, created_at=utcnow())
        db.session.add(user)
        db.session.flush()
        entry = AuditLog(
            user_id=user.id,
            action="auth.login",
            resource_type="user",
            resource_id=str(user.id),
            created_at=utcnow(),
        )
        db.session.add(entry)
        db.session.commit()
        entry_id = entry.id
        db.session.delete(user)
        db.session.commit()
        db.session.expire_all()
        stored = db.session.get(AuditLog, entry_id)
        assert stored.user_id is None


def test_session_cookie_flags(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["SESSION_COOKIE_SECURE"] is False
