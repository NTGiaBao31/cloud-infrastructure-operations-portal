from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select

from app.extensions import db
from app.models import Server, utcnow
from app.services.audit import record
from app.services.inventory import LAB_TARGETS
from app.services.probes import http_probe, tcp_probe, unpack_probe
from app.services.prometheus import client_from_app

CLUSTER_QUERIES = {
    "availability": "avg(up) * 100",
    "cpu": '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
    "memory": "(1 - (avg(node_memory_MemAvailable_bytes) / avg(node_memory_MemTotal_bytes))) * 100",
    "disk": (
        "100 * (1 - avg(node_filesystem_avail_bytes{fstype!~\"tmpfs|overlay\"}) "
        '/ avg(node_filesystem_size_bytes{fstype!~"tmpfs|overlay"}))'
    ),
}

LINUX_QUERIES = {
    "cpu": '100 - (avg(rate(node_cpu_seconds_total{{mode="idle",instance="{instance}"}}[5m])) * 100)',
    "memory": (
        "(1 - (avg(node_memory_MemAvailable_bytes{{instance=\"{instance}\"}}) "
        '/ avg(node_memory_MemTotal_bytes{{instance="{instance}"}}))) * 100'
    ),
    "disk": (
        "100 * (1 - avg(node_filesystem_avail_bytes{{instance=\"{instance}\",fstype!~\"tmpfs|overlay\"}}) "
        '/ avg(node_filesystem_size_bytes{{instance="{instance}",fstype!~"tmpfs|overlay"}}))'
    ),
    "uptime": '(time() - node_boot_time_seconds{{instance="{instance}"}})',
}

WINDOWS_QUERIES = {
    "cpu": '100 - (avg(rate(windows_cpu_time_total{{mode="idle",instance="{instance}"}}[5m])) * 100)',
    "memory": (
        "(1 - (avg(windows_os_physical_memory_free_bytes{{instance=\"{instance}\"}}) "
        '/ avg(windows_cs_physical_memory_bytes{{instance="{instance}"}}))) * 100'
    ),
    "disk": (
        "100 * (1 - avg(windows_logical_disk_free_bytes{{instance=\"{instance}\"}}) "
        '/ avg(windows_logical_disk_size_bytes{{instance="{instance}"}}))'
    ),
    "uptime": '(time() - windows_os_start_time{{instance="{instance}"}})',
}

WINDOWS_MEMORY_FALLBACK = (
    "(1 - (avg(windows_memory_available_bytes{{instance=\"{instance}\"}}) "
    '/ avg(windows_cs_physical_memory_bytes{{instance="{instance}"}}))) * 100'
)

HOST_CHECKS = {
    "WEB01": {
        "role": "Web Server",
        "exporter_label": "Node Exporter :9100",
        "exporter_short": "E",
        "services": [
            {"name": "Nginx :80", "short": "N", "kind": "http", "url": "http://192.168.10.11/"},
        ],
    },
    "APP01": {
        "role": "Application Server",
        "exporter_label": "Node Exporter :9100",
        "exporter_short": "E",
        "services": [
            {"name": "App :8080", "short": "A", "kind": "http", "url": "http://192.168.10.12:8080/"},
        ],
    },
    "WIN01": {
        "role": "Windows Server",
        "exporter_label": "Windows Exporter :9182",
        "exporter_short": "E",
        "services": [
            {
                "name": "WinRM :5985",
                "short": "W",
                "kind": "tcp",
                "host": "192.168.10.13",
                "port": 5985,
            }
        ],
    },
    "MON01": {
        "role": "Monitoring Server",
        "exporter_label": "Node Exporter :9100",
        "exporter_short": "E",
        "services": [
            {
                "name": "Prometheus :9090",
                "short": "P",
                "kind": "http",
                "url": "http://192.168.10.10:9090/-/healthy",
            },
            {
                "name": "Alertmanager :9093",
                "short": "AM",
                "kind": "http",
                "url": "http://192.168.10.10:9093/-/healthy",
            },
            {
                "name": "Grafana :3000",
                "short": "G",
                "kind": "http",
                "url": "http://192.168.10.10:3000/",
            },
        ],
    },
}

INVENTORY_STATUS = {"Healthy": "online", "Degraded": "warning", "Unreachable": "down"}


def collect_metrics(probe_http=None, probe_tcp=None):
    probe_http = http_probe if probe_http is None else probe_http
    probe_tcp = tcp_probe if probe_tcp is None else probe_tcp
    values = {name: "N/A" for name in CLUSTER_QUERIES}
    client = client_from_app()
    status = client.health()
    _note_backend(status)
    if status.available:
        for name, query in CLUSTER_QUERIES.items():
            values[name] = _percent_pair(client.instant_query(query))[0]
    timeout = _probe_timeout()
    hosts = [
        _collect_host(name, spec, client, status.available, probe_http, probe_tcp, timeout)
        for name, spec in LAB_TARGETS.items()
    ]
    _apply_live_status(hosts)
    return values, hosts, status


def empty_hosts():
    return [_blank_host(name) for name in LAB_TARGETS]


def _blank_host(name):
    spec = LAB_TARGETS[name]
    check = HOST_CHECKS[name]
    return {
        "name": name,
        "role": check["role"],
        "ip": spec["ip_address"],
        "instance": spec["monitoring_target"],
        "status": "Unreachable",
        "cpu": "N/A",
        "memory": "N/A",
        "disk": "N/A",
        "uptime": "N/A",
        "cpu_value": None,
        "memory_value": None,
        "disk_value": None,
        "exporter_label": check["exporter_label"],
        "exporter_short": check["exporter_short"],
        "exporter": "DOWN",
        "services": [
            {"name": item["name"], "short": item["short"], "status": "DOWN", "latency_ms": None}
            for item in check["services"]
        ],
    }


def _collect_host(name, spec, client, prometheus_available, probe_http, probe_tcp, timeout):
    row = _blank_host(name)
    check = HOST_CHECKS[name]
    if prometheus_available:
        up_value = _numeric(client.instant_query(f'up{{instance="{spec["monitoring_target"]}"}}'))
        exporter_up = up_value is not None and up_value >= 1
    else:
        exporter_up = False
    row["exporter"] = "UP" if exporter_up else "DOWN"

    jobs = []
    for item in check["services"]:
        jobs.append((item, probe_http, probe_tcp, timeout))
    results = _run_probes(jobs)
    services = []
    service_up = True
    for item, ok, latency in results:
        services.append(
            {
                "name": item["name"],
                "short": item["short"],
                "status": "UP" if ok else "DOWN",
                "latency_ms": latency,
            }
        )
        service_up = service_up and ok
    row["services"] = services
    row["status"] = _host_status(exporter_up, service_up)

    if prometheus_available and exporter_up:
        queries = WINDOWS_QUERIES if spec["os_type"] == "windows" else LINUX_QUERIES
        instance = spec["monitoring_target"]
        for metric, template in queries.items():
            result = client.instant_query(template.format(instance=instance))
            if metric == "uptime":
                row[metric] = _format_uptime(result)
            else:
                text, numeric = _percent_pair(result)
                row[metric] = text
                row[f"{metric}_value"] = numeric
        if spec["os_type"] == "windows" and row["memory_value"] is None:
            text, numeric = _percent_pair(client.instant_query(WINDOWS_MEMORY_FALLBACK.format(instance=instance)))
            row["memory"] = text
            row["memory_value"] = numeric
    return row


def _run_probes(jobs):
    if len(jobs) <= 1:
        return [_probe_one(*job) for job in jobs]
    with ThreadPoolExecutor(max_workers=min(8, len(jobs))) as pool:
        return list(pool.map(lambda job: _probe_one(*job), jobs))


def _probe_one(item, probe_http, probe_tcp, timeout):
    if item["kind"] == "http":
        result = probe_http(item["url"], timeout=timeout)
    else:
        result = probe_tcp(item["host"], item["port"], timeout=timeout)
    ok, latency = unpack_probe(result)
    return item, ok, latency


def _host_status(exporter_up, service_up):
    if exporter_up and service_up:
        return "Healthy"
    if not exporter_up and not service_up:
        return "Unreachable"
    return "Degraded"


def _apply_live_status(hosts):
    now = utcnow()
    for host in hosts:
        mapped = INVENTORY_STATUS.get(host["status"])
        if mapped is None:
            continue
        server = db.session.scalar(select(Server).where(Server.name == host["name"]))
        if server is None:
            continue
        server.status = mapped
        if mapped in {"online", "warning"}:
            server.last_seen_at = now
        host["server_id"] = server.id
        host["last_seen_at"] = server.last_seen_at
    db.session.commit()


def _note_backend(status):
    from flask import current_app, has_app_context

    if not has_app_context():
        return
    last = current_app.config.get("_PROMETHEUS_LAST_AVAILABLE")
    current_app.config["_PROMETHEUS_LAST_AVAILABLE"] = status.available
    if status.available:
        return
    if last is True or last is None:
        record(
            "prometheus.unavailable",
            "prometheus",
            None,
            {"message": status.message or "Monitoring backend unavailable"},
        )


def _probe_timeout():
    from flask import current_app, has_app_context

    if has_app_context():
        return float(current_app.config.get("PROBE_TIMEOUT_SECONDS", 2))
    return 2.0


def _numeric(result):
    raw = _raw_value(result)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _percent_pair(result):
    value = _numeric(result)
    if value is None:
        return "N/A", None
    return f"{value:.1f}%", round(value, 1)


def _format_uptime(result):
    value = _numeric(result)
    if value is None or value < 0:
        return "N/A"
    seconds = int(value)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h"
    return f"{hours}h {minutes}m"


def _raw_value(result):
    if not result.available or not isinstance(result.data, dict):
        return None
    samples = result.data.get("result")
    if not isinstance(samples, list) or not samples:
        return None
    sample = samples[0]
    if isinstance(sample, dict) and isinstance(sample.get("value"), list) and len(sample["value"]) > 1:
        return sample["value"][1]
    return None
