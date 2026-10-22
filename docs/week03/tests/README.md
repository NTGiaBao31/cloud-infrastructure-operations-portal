# Tests tuần 3

Từ `E:\KLTN`:

```powershell
.venv\Scripts\python -m pytest tests/test_pages.py tests/test_prometheus.py tests/test_alert_webhook.py tests/test_inventory.py tests/test_alert_sync.py -q
```

Phủ:

- RBAC và các trang khi Prometheus tắt (`test_pages.py`, `test_auth_rbac.py`)
- Prometheus malformed/timeout → N/A
- Webhook firing/resolved, map WEB01, không duplicate
- Mapping instance → WEB01/WIN01/MON01
- Failure handling: dashboard 200, Monitoring Backend Unavailable
