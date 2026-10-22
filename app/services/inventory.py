from sqlalchemy import select

from app.models import Server

LAB_TARGETS = {
    "WEB01": {
        "hostname": "WEB01",
        "ip_address": "192.168.10.11",
        "os_type": "linux",
        "monitoring_target": "192.168.10.11:9100",
        "environment": "prod",
        "automation_group": "linux_web",
    },
    "APP01": {
        "hostname": "APP01",
        "ip_address": "192.168.10.12",
        "os_type": "linux",
        "monitoring_target": "192.168.10.12:9100",
        "environment": "prod",
        "automation_group": "linux_app",
    },
    "WIN01": {
        "hostname": "WIN01",
        "ip_address": "192.168.10.13",
        "os_type": "windows",
        "monitoring_target": "192.168.10.13:9182",
        "environment": "prod",
        "automation_group": "windows_app",
    },
    "MON01": {
        "hostname": "MON01",
        "ip_address": "192.168.10.10",
        "os_type": "linux",
        "monitoring_target": "192.168.10.10:9100",
        "environment": "prod",
        "automation_group": "linux_mon",
    },
}

INSTANCE_ALIASES = {
    "192.168.10.11:9100": "WEB01",
    "192.168.10.11": "WEB01",
    "web01": "WEB01",
    "192.168.10.12:9100": "APP01",
    "192.168.10.12": "APP01",
    "app01": "APP01",
    "192.168.10.13:9182": "WIN01",
    "192.168.10.13": "WIN01",
    "win01": "WIN01",
    "192.168.10.10:9100": "MON01",
    "localhost:9090": "MON01",
    "127.0.0.1:9090": "MON01",
    "192.168.10.10:9090": "MON01",
    "192.168.10.10": "MON01",
    "mon01": "MON01",
}


def instance_candidates(*values):
    found = []
    for value in values:
        if not value:
            continue
        text = str(value).strip()
        if not text or text in found:
            continue
        found.append(text)
        if ":" in text:
            host = text.split(":", 1)[0]
            if host not in found:
                found.append(host)
    return found


def canonical_server_name(instance):
    if not instance:
        return None
    key = str(instance).strip()
    if key in INSTANCE_ALIASES:
        return INSTANCE_ALIASES[key]
    host = key.split(":", 1)[0]
    return INSTANCE_ALIASES.get(host) or INSTANCE_ALIASES.get(host.lower())


def match_server(*values, labels=None):
    candidates = list(instance_candidates(*values))
    if labels:
        for key in ("instance", "monitoring_target", "hostname", "host", "ip", "job"):
            raw = labels.get(key)
            if raw:
                candidates.extend(instance_candidates(raw))
    seen = []
    for candidate in candidates:
        if candidate not in seen:
            seen.append(candidate)
    servers = list(db_servers())
    by_target = {server.monitoring_target: server for server in servers if server.monitoring_target}
    by_name = {server.name: server for server in servers}
    by_host = {server.hostname: server for server in servers}
    by_ip = {server.ip_address: server for server in servers}
    for candidate in seen:
        mapped = canonical_server_name(candidate)
        if mapped and mapped in by_name:
            return by_name[mapped]
        if candidate in by_target:
            return by_target[candidate]
        if candidate in by_name:
            return by_name[candidate]
        if candidate in by_host:
            return by_host[candidate]
        if candidate in by_ip:
            return by_ip[candidate]
    return None


def db_servers():
    from app.extensions import db

    return list(db.session.scalars(select(Server)))
