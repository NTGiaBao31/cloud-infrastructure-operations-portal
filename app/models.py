from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin', 'operator', 'viewer')", name="ck_users_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Server(db.Model):
    __tablename__ = "servers"
    __table_args__ = (
        CheckConstraint("os_type IN ('linux', 'windows')", name="ck_servers_os_type"),
        CheckConstraint(
            "status IN ('online', 'warning', 'down', 'maintenance', 'unknown')",
            name="ck_servers_status",
        ),
        Index("ix_servers_status", "status"),
        Index("ix_servers_environment", "environment"),
        Index("ix_servers_os_type", "os_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    environment: Mapped[str] = mapped_column(String(40), nullable=False)
    os_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    monitoring_target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    automation_group: Mapped[str | None] = mapped_column(String(120), nullable=True)
    azure_resource_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    alerts: Mapped[list["Alert"]] = relationship(back_populates="server")
    jobs: Mapped[list["AutomationJob"]] = relationship(back_populates="server")


class Alert(db.Model):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint("severity IN ('critical', 'warning', 'info')", name="ck_alerts_severity"),
        CheckConstraint("status IN ('firing', 'acknowledged', 'resolved')", name="ck_alerts_status"),
        Index("ix_alerts_fingerprint", "fingerprint"),
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_severity", "severity"),
        Index("ix_alerts_server_id", "server_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    server_id: Mapped[int | None] = mapped_column(
        ForeignKey("servers.id", ondelete="SET NULL", name="fk_alerts_server_id"),
        nullable=True,
    )
    acknowledged_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL", name="fk_alerts_acknowledged_by"),
        nullable=True,
    )
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    alert_name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    summary: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    server: Mapped[Server | None] = relationship(back_populates="alerts")
    acknowledger: Mapped[User | None] = relationship(foreign_keys=[acknowledged_by])
    jobs: Mapped[list["AutomationJob"]] = relationship(back_populates="alert")


class AutomationJob(db.Model):
    __tablename__ = "automation_jobs"
    __table_args__ = (
        CheckConstraint(
            "trigger_source IN ('manual', 'remediation', 'system')",
            name="ck_automation_jobs_trigger_source",
        ),
        CheckConstraint(
            "executor IN ('mock', 'ansible', 'powershell', 'shell')",
            name="ck_automation_jobs_executor",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'canceled')",
            name="ck_automation_jobs_status",
        ),
        Index("ix_automation_jobs_status", "status"),
        Index("ix_automation_jobs_server_id", "server_id"),
        Index("ix_automation_jobs_alert_id", "alert_id"),
        Index("ix_automation_jobs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    server_id: Mapped[int | None] = mapped_column(
        ForeignKey("servers.id", ondelete="SET NULL", name="fk_automation_jobs_server_id"),
        nullable=True,
    )
    alert_id: Mapped[int | None] = mapped_column(
        ForeignKey("alerts.id", ondelete="SET NULL", name="fk_automation_jobs_alert_id"),
        nullable=True,
    )
    requested_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL", name="fk_automation_jobs_requested_by"),
        nullable=True,
    )
    trigger_source: Mapped[str] = mapped_column(String(20), nullable=False)
    executor: Mapped[str] = mapped_column(String(20), nullable=False)
    action_key: Mapped[str] = mapped_column(String(80), nullable=False)
    parameters_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    server: Mapped[Server | None] = relationship(back_populates="jobs")
    alert: Mapped[Alert | None] = relationship(back_populates="jobs")
    requester: Mapped[User | None] = relationship(foreign_keys=[requested_by])


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_resource_type", "resource_type"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL", name="fk_audit_logs_user_id"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    user: Mapped[User | None] = relationship(foreign_keys=[user_id], passive_deletes=True)
