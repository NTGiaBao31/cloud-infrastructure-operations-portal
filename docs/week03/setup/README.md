# Setup — chạy portal độc lập trên laptop

Yêu cầu: Python 3.11, Tailscale đã vào mạng lab, SQLite local.

```powershell
cd E:\KLTN
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Trong `.env`:

- `PROMETHEUS_BASE_URL=http://192.168.10.10:9090`
- `GRAFANA_BASE_URL=http://192.168.10.10:3000`
- `DATABASE_URL=sqlite:///instance/portal.db`
- `DEMO_USER_PASSWORD` và `SECRET_KEY`

```powershell
.venv\Scripts\flask --app wsgi db upgrade
.venv\Scripts\flask --app wsgi seed-demo
.venv\Scripts\flask --app wsgi run --host 127.0.0.1 --port 5000
```

Mở http://127.0.0.1:5000 — tài khoản `admin` / `operator` / `viewer`.

Kiểm tra đường Prometheus từ laptop:

```powershell
Test-NetConnection 192.168.10.10 -Port 9090
```

Alertmanager gọi webhook về laptop. Máy MON01 phải tới được IP Tailscale của laptop, ví dụ:

`http://<tailscale-ip-laptop>:5000/api/alerts/webhook`
