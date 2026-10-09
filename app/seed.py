import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.extensions import db
from app.models import Alert, AuditLog, AutomationJob, Server, User

BASE = datetime(2026, 10, 1, tzinfo=timezone.utc)


class SeedError(RuntimeError):
    pass


def _at(hours):
    return BASE + timedelta(hours=hours)


def _load_json(text):
    try:
        return json.loads(text or "{}")
    except json.JSONDecodeError:
        return {}


def _find_tagged(model, column, demo_key):
    rows = db.session.scalars(select(model)).all()
    for row in rows:
        if _load_json(getattr(row, column)).get("demo_key") == demo_key:
            return row
    return None


def seed_demo_data():
    from flask import current_app

    password = current_app.config.get("DEMO_USER_PASSWORD") or ""
    if not password:
        raise SeedError("DEMO_USER_PASSWORD is not set")
    users = _seed_users(password)
    servers = _seed_servers()
    alerts = _seed_alerts(servers, users)
    jobs = _seed_jobs(servers, alerts, users)
    _seed_audits(users, servers, alerts, jobs)
    db.session.commit()
    return {
        "users": len(users),
        "servers": len(servers),
        "alerts": len(alerts),
        "jobs": len(jobs),
        "audits": 12,
    }


def _seed_users(password):
    specs = [
        ("admin", "admin", _at(1)),
        ("operator", "operator", _at(2)),
        ("viewer", "viewer", _at(3)),
    ]
    found = {}
    for username, role, last_login in specs:
        user = db.session.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(username=username, role=role, created_at=_at(0))
            db.session.add(user)
        user.role = role
        user.is_active = True
        user.last_login_at = last_login
        user.set_password(password)
        found[username] = user
    db.session.flush()
    return found


def _seed_servers():
    specs = [
        {
            "name": "web-01",
            "hostname": "web-01.local",
            "ip_address": "10.0.0.11",
            "environment": "prod",
            "os_type": "linux",
            "status": "online",
            "monitoring_target": "web-01.local",
            "automation_group": "linux_web",
            "azure_resource_id": None,
            "last_seen_at": _at(20),
        },
        {
            "name": "db-01",
            "hostname": "db-01.local",
            "ip_address": "10.0.0.12",
            "environment": "prod",
            "os_type": "linux",
            "status": "warning",
            "monitoring_target": "db-01.local",
            "automation_group": "linux_db",
            "azure_resource_id": None,
            "last_seen_at": _at(19),
        },
        {
            "name": "worker-01",
            "hostname": "worker-01.local",
            "ip_address": "10.0.0.13",
            "environment": "prod",
            "os_type": "linux",
            "status": "down",
            "monitoring_target": "worker-01.local",
            "automation_group": "linux_worker",
            "azure_resource_id": None,
            "last_seen_at": _at(12),
        },
        {
            "name": "app-win-01",
            "hostname": "app-win-01.local",
            "ip_address": "10.0.1.21",
            "environment": "staging",
            "os_type": "windows",
            "status": "maintenance",
            "monitoring_target": "app-win-01.local",
            "automation_group": "windows_app",
            "azure_resource_id": None,
            "last_seen_at": _at(8),
        },
        {
            "name": "iis-01",
            "hostname": "iis-01.local",
            "ip_address": "10.0.1.22",
            "environment": "prod",
            "os_type": "windows",
            "status": "unknown",
            "monitoring_target": "iis-01.local",
            "automation_group": "windows_iis",
            "azure_resource_id": None,
            "last_seen_at": None,
        },
        {
            "name": "azure-vm-01",
            "hostname": "azure-vm-01.local",
            "ip_address": "10.1.0.31",
            "environment": "prod",
            "os_type": "linux",
            "status": "online",
            "monitoring_target": "azure-vm-01.local",
            "automation_group": "azure_linux",
            "azure_resource_id": (
                "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/"
                "rg-demo/providers/Microsoft.Compute/virtualMachines/azure-vm-01"
            ),
            "last_seen_at": _at(21),
        },
    ]
    found = {}
    for spec in specs:
        server = db.session.scalar(select(Server).where(Server.name == spec["name"]))
        if server is None:
            server = Server(name=spec["name"], created_at=_at(0))
            db.session.add(server)
        for key, value in spec.items():
            setattr(server, key, value)
        server.is_active = True
        server.updated_at = _at(22)
        found[spec["name"]] = server
    db.session.flush()
    return found


def _seed_alerts(servers, users):
    specs = [
        ("demo-fp-service-down-web", "service_down", "availability", "critical", "firing", "web-01", "nginx is down", "The nginx service is not running.", None, 10, None),
        ("demo-fp-container-down-worker", "container_down", "availability", "warning", "firing", "worker-01", "worker container is down", "Container worker has exited.", None, 11, None),
        ("demo-fp-disk-high-db", "disk_high", "capacity", "warning", "acknowledged", "db-01", "Disk usage above 85 percent", "Root filesystem is filling up.", "operator", 6, 9),
        ("demo-fp-service-down-iis", "service_down", "availability", "info", "resolved", "iis-01", "W3SVC was restarted", "IIS service recovered.", None, 4, 7),
        ("demo-fp-disk-high-azure", "disk_high", "capacity", "critical", "firing", "azure-vm-01", "Azure VM disk is critical", "OS disk usage is above 95 percent.", None, 14, None),
        ("demo-fp-container-down-web", "container_down", "availability", "info", "resolved", "web-01", "sidecar container recovered", "Sidecar restarted cleanly.", None, 3, 5),
        ("demo-fp-disk-high-worker", "disk_high", "capacity", "info", "acknowledged", "worker-01", "Log volume growing", "Worker logs are using extra disk.", "admin", 8, 13),
    ]
    found = {}
    for fingerprint, name, category, severity, status, server_name, summary, description, ack_user, start_h, ack_h in specs:
        alert = db.session.scalar(select(Alert).where(Alert.fingerprint == fingerprint))
        if alert is None:
            alert = Alert(fingerprint=fingerprint, created_at=_at(start_h))
            db.session.add(alert)
        alert.server_id = servers[server_name].id
        alert.alert_name = name
        alert.category = category
        alert.source = "demo"
        alert.severity = severity
        alert.status = status
        alert.summary = summary
        alert.description = description
        alert.starts_at = _at(start_h)
        alert.acknowledged_by = users[ack_user].id if ack_user else None
        alert.acknowledged_at = _at(ack_h) if ack_h and status == "acknowledged" else None
        alert.resolved_at = _at(start_h + 2) if status == "resolved" else None
        found[fingerprint] = alert
    db.session.flush()
    return found


def _seed_jobs(servers, alerts, users):
    specs = [
        {
            "demo_key": "demo-job-1",
            "server": "web-01",
            "alert": "demo-fp-service-down-web",
            "user": "operator",
            "trigger_source": "manual",
            "executor": "mock",
            "action_key": "restart_service",
            "params": {"service_name": "nginx"},
            "status": "succeeded",
            "exit_code": 0,
            "output": "Mock executor completed restart_service.",
            "created_h": 15,
        },
        {
            "demo_key": "demo-job-2",
            "server": "worker-01",
            "alert": "demo-fp-container-down-worker",
            "user": "admin",
            "trigger_source": "remediation",
            "executor": "mock",
            "action_key": "restart_container",
            "params": {"container_name": "worker"},
            "status": "failed",
            "exit_code": 1,
            "output": "Mock executor simulated failure.",
            "created_h": 16,
        },
        {
            "demo_key": "demo-job-3",
            "server": "db-01",
            "alert": "demo-fp-disk-high-db",
            "user": "operator",
            "trigger_source": "manual",
            "executor": "mock",
            "action_key": "disk_cleanup",
            "params": {"path": "var-log", "dry_run": "true"},
            "status": "queued",
            "exit_code": None,
            "output": None,
            "created_h": 17,
        },
        {
            "demo_key": "demo-job-4",
            "server": "azure-vm-01",
            "alert": "demo-fp-disk-high-azure",
            "user": "admin",
            "trigger_source": "remediation",
            "executor": "mock",
            "action_key": "restart_service",
            "params": {"service_name": "app"},
            "status": "running",
            "exit_code": None,
            "output": None,
            "created_h": 18,
        },
        {
            "demo_key": "demo-job-5",
            "server": "web-01",
            "alert": None,
            "user": "admin",
            "trigger_source": "manual",
            "executor": "ansible",
            "action_key": "restart_service",
            "params": {"service_name": "nginx"},
            "status": "succeeded",
            "exit_code": 0,
            "output": "Illustrated Ansible result. Real execution is disabled in MVP.",
            "created_h": 18,
        },
        {
            "demo_key": "demo-job-6",
            "server": "app-win-01",
            "alert": None,
            "user": "operator",
            "trigger_source": "manual",
            "executor": "powershell",
            "action_key": "restart_service",
            "params": {"service_name": "W3SVC"},
            "status": "failed",
            "exit_code": 1,
            "output": "Illustrated PowerShell result. Real execution is disabled in MVP.",
            "created_h": 19,
        },
        {
            "demo_key": "demo-job-7",
            "server": "iis-01",
            "alert": None,
            "user": "admin",
            "trigger_source": "system",
            "executor": "shell",
            "action_key": "disk_cleanup",
            "params": {"path": "tmp", "dry_run": "true"},
            "status": "succeeded",
            "exit_code": 0,
            "output": "Illustrated shell result. Real execution is disabled in MVP.",
            "created_h": 19,
        },
        {
            "demo_key": "demo-job-8",
            "server": "worker-01",
            "alert": None,
            "user": "operator",
            "trigger_source": "manual",
            "executor": "mock",
            "action_key": "restart_container",
            "params": {"container_name": "worker"},
            "status": "queued",
            "exit_code": None,
            "output": None,
            "created_h": 20,
        },
    ]
    found = {}
    for spec in specs:
        job = _find_tagged(AutomationJob, "parameters_json", spec["demo_key"])
        if job is None:
            job = AutomationJob(
                trigger_source=spec["trigger_source"],
                executor=spec["executor"],
                action_key=spec["action_key"],
                parameters_json="{}",
                created_at=_at(spec["created_h"]),
            )
            db.session.add(job)
        params = dict(spec["params"])
        params["demo_key"] = spec["demo_key"]
        job.server_id = servers[spec["server"]].id
        job.alert_id = alerts[spec["alert"]].id if spec["alert"] else None
        job.requested_by = users[spec["user"]].id
        job.trigger_source = spec["trigger_source"]
        job.executor = spec["executor"]
        job.action_key = spec["action_key"]
        job.parameters_json = json.dumps(params, sort_keys=True)
        job.status = spec["status"]
        job.exit_code = spec["exit_code"]
        job.output_excerpt = spec["output"]
        job.created_at = _at(spec["created_h"])
        job.started_at = _at(spec["created_h"]) if spec["status"] in {"running", "succeeded", "failed"} else None
        job.finished_at = _at(spec["created_h"] + 1) if spec["status"] in {"succeeded", "failed"} else None
        found[spec["demo_key"]] = job
    db.session.flush()
    return found


def _seed_audits(users, servers, alerts, jobs):
    specs = [
        ("demo-audit-01", "auth.login", "user", users["admin"].id, "admin", {}),
        ("demo-audit-02", "auth.login", "user", users["operator"].id, "operator", {}),
        ("demo-audit-03", "auth.login", "user", users["viewer"].id, "viewer", {}),
        ("demo-audit-04", "auth.logout", "user", users["admin"].id, "admin", {}),
        ("demo-audit-05", "alert.acknowledge", "alert", alerts["demo-fp-disk-high-db"].id, "operator", {"fingerprint": "demo-fp-disk-high-db"}),
        ("demo-audit-06", "job.request", "automation_job", jobs["demo-job-1"].id, "operator", {"demo_job": "demo-job-1"}),
        ("demo-audit-07", "job.result", "automation_job", jobs["demo-job-1"].id, "operator", {"demo_job": "demo-job-1", "status": "succeeded"}),
        ("demo-audit-08", "server.update", "server", servers["web-01"].id, "admin", {"field": "status"}),
        ("demo-audit-09", "server.create", "server", servers["azure-vm-01"].id, "admin", {}),
        ("demo-audit-10", "remediation.request", "alert", alerts["demo-fp-container-down-worker"].id, "admin", {"action_key": "restart_container"}),
        ("demo-audit-11", "job.result", "automation_job", jobs["demo-job-2"].id, "admin", {"demo_job": "demo-job-2", "status": "failed"}),
        ("demo-audit-12", "alert.acknowledge", "alert", alerts["demo-fp-disk-high-worker"].id, "admin", {"fingerprint": "demo-fp-disk-high-worker"}),
    ]
    for index, (demo_key, action, resource_type, resource_id, actor, details) in enumerate(specs, start=1):
        entry = _find_tagged(AuditLog, "details_json", demo_key)
        if entry is None:
            entry = AuditLog(action=action, resource_type=resource_type, created_at=_at(index))
            db.session.add(entry)
        payload = dict(details)
        payload["demo_key"] = demo_key
        entry.user_id = users[actor].id
        entry.action = action
        entry.resource_type = resource_type
        entry.resource_id = str(resource_id)
        entry.details_json = json.dumps(payload, sort_keys=True)
        entry.ip_address = "127.0.0.1"
        entry.created_at = _at(index)
    db.session.flush()
