# Cloud Infrastructure Operations Portal

Local Flask portal for server inventory, alerts, mock automation, and audit history.

Python 3.11, SQLite, and an English Bootstrap UI. Prometheus, Grafana, Ansible, PowerShell, Shell, and Azure stay behind adapters. The portal still runs when those services are absent. Automation defaults to a mock executor and does not change target machines.

## Design Documents

- [Application architecture](docs/application-architecture.md)
- [Entity relationship diagram](docs/erd.md)
- [UI wireframes](docs/ui-wireframes.md)
- [Prometheus and Ansible integration plan](docs/prometheus-ansible-integration-plan.md)

## Setup

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `SECRET_KEY` and `DEMO_USER_PASSWORD` in `.env` before seeding.

```powershell
.venv\Scripts\flask --app wsgi db upgrade
.venv\Scripts\flask --app wsgi seed-demo
.venv\Scripts\flask --app wsgi run
```

Open http://127.0.0.1:5000 and sign in as `admin`, `operator`, or `viewer`.

## Checks

```powershell
.venv\Scripts\python -m pytest
.venv\Scripts\flask --app wsgi sync-prometheus-alerts
```

`/healthz` does not require a session. `sync-prometheus-alerts` exits non-zero when Prometheus cannot be reached and leaves existing alerts unchanged.
