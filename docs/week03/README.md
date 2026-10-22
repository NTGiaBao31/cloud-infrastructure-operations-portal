# Application — Tuần 3

Portal chạy trên laptop, SQLite giữ nguyên. Prometheus nằm trên MON01 (`192.168.10.10:9090`). Đường đi: laptop → Tailscale → MGMT01 → MON01.

## Việc đã làm

- Chuẩn hóa thư mục `docs/week03/`.
- Gọi Prometheus API, lấy live status/metrics cho WEB01, APP01, WIN01, MON01.
- Dashboard theo 4 nhóm: Host status (Healthy/Degraded/Unreachable), CPU/RAM/Disk/Uptime, exporter UP/DOWN, probe HTTP/TCP (Nginx :80, App :8080, WinRM :5985, Prometheus :9090, Alertmanager :9093, Grafana :3000). Monitoring backend là Prometheus API, tách khỏi metric host MON01 `:9100`.
- Khi MON01/Prometheus tắt: portal không crash, metrics hiện N/A, Monitoring backend **Down**, Inventory/Audit/Jobs vẫn mở.
- Webhook `POST /api/alerts/webhook` nhận Alertmanager, map `192.168.10.11:9100` → WEB01, lưu SQLite, chống trùng fingerprint, cập nhật firing → resolved.
- Audit: `alert.received`, `alert.resolved`, `prometheus.unavailable`, `automation.trigger` nếu bật auto-remediation.

## Luồng sự cố

WEB01 down → Prometheus InstanceDown → Alertmanager → Flask webhook → SQLite → Alerts UI.

Khi WEB01 lên lại, cùng fingerprint chuyển **resolved**, không tạo bản ghi mới.

## Máy chủ lab

| Tên | IP | Target |
| --- | --- | --- |
| MGMT01 | 192.168.10.5 | — |
| MON01 | 192.168.10.10 | Prometheus `:9090`, Grafana `:3000`, Alertmanager `:9093` |
| WEB01 | 192.168.10.11 | `192.168.10.11:9100` |
| APP01 | 192.168.10.12 | `192.168.10.12:9100` |
| WIN01 | 192.168.10.13 | `192.168.10.13:9182` |

Trên GitHub nhóm, đặt các file này tại `application/docs/week03/`.
