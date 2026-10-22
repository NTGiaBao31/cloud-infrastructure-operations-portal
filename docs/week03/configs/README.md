# Configs

Xem `.env.example` ở gốc repo và bản copy `portal.env.example` trong thư mục này.

| Biến | Tuần 3 |
| --- | --- |
| `PROMETHEUS_BASE_URL` | `http://192.168.10.10:9090` |
| `PROMETHEUS_TIMEOUT_SECONDS` | `3` |
| `GRAFANA_BASE_URL` | `http://192.168.10.10:3000` |
| `ALERTMANAGER_WEBHOOK_TOKEN` | để trống nếu lab chưa gắn token; nếu có thì Alertmanager gửi `X-Webhook-Token` |
| `AUTO_REMEDIATION_ENABLED` | `false` |

Mapping instance:

- `192.168.10.11:9100` → WEB01 host metrics
- `192.168.10.12:9100` → APP01 host metrics
- `192.168.10.13:9182` → WIN01 host metrics
- `192.168.10.10:9100` → MON01 host metrics (CPU/RAM/Disk/Uptime)
- `localhost:9090` / `192.168.10.10:9090` → Prometheus service health / monitoring backend, mapped to MON01
