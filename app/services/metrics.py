from app.services.prometheus import client_from_app

QUERIES = {
    "availability": "avg(up) * 100",
    "cpu": '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
    "memory": "(1 - (avg(node_memory_MemAvailable_bytes) / avg(node_memory_MemTotal_bytes))) * 100",
    "disk": (
        "100 * (1 - avg(node_filesystem_avail_bytes{fstype!~\"tmpfs|overlay\"}) "
        '/ avg(node_filesystem_size_bytes{fstype!~"tmpfs|overlay"}))'
    ),
}


def collect_metrics():
    values = {name: "N/A" for name in QUERIES}
    client = client_from_app()
    status = client.health()
    if not status.available:
        return values, status
    for name, query in QUERIES.items():
        result = client.instant_query(query)
        values[name] = _format_result(result)
    return values, status


def _format_result(result):
    if not result.available or not isinstance(result.data, dict):
        return "N/A"
    samples = result.data.get("result")
    if not isinstance(samples, list) or not samples:
        return "N/A"
    sample = samples[0]
    raw = None
    if isinstance(sample, dict) and isinstance(sample.get("value"), list) and len(sample["value"]) > 1:
        raw = sample["value"][1]
    if raw is None:
        return "N/A"
    try:
        return f"{float(raw):.1f}%"
    except (TypeError, ValueError):
        return "N/A"
