# UI Wireframes

The portal uses a shared Bootstrap layout with role-based navigation. These wireframes describe the implemented MVP screens.

## Login

```text
+------------------------------------------------------------+
|                    Operations Portal                       |
|                                                            |
|  Username  [________________________________]              |
|  Password  [________________________________]              |
|                                                            |
|                    [ Sign in ]                             |
+------------------------------------------------------------+
```

## Dashboard

```text
+------------------------------------------------------------+
| Brand | Dashboard | Servers | Alerts | Automation | Audit  |
+------------------------------------------------------------+
| Dashboard                              Prometheus: status  |
| [Servers] [Open alerts] [Critical] [Warning]               |
| [Online] [Warning] [Down] [Maintenance] [Unknown]          |
| Live metrics: [Availability] [CPU] [Memory] [Disk]         |
| Grafana: [ Open Grafana ] or configuration message          |
| Recent jobs: Action | Status | Executor | When              |
+------------------------------------------------------------+
```

## Server Inventory

```text
+------------------------------------------------------------+
| Servers                                         [Add server]|
| [Status v] [OS v] [Environment____________] [Filter]        |
| Name        Address       Environment  OS      Status Active|
| server-01   10.0.0.10     production   Linux   online yes   |
+------------------------------------------------------------+
```

Selecting a server opens its details and, for administrators, edit and activate/deactivate controls.

## Operations Screens

```text
+------------------------------------------------------------+
| Alerts: Severity | Alert | Server | Status | [Acknowledge] |
+------------------------------------------------------------+
| Automation: Server [v] Action [v] Parameters [...] [Run]   |
| Job history: action | target | executor | status | time     |
+------------------------------------------------------------+
| Audit: Time | User | Action | Resource | Details           |
+------------------------------------------------------------+
```

## Role Access

| Role | Access |
| --- | --- |
| Viewer | View dashboard, inventory, alerts, jobs, and audit history. |
| Operator | Viewer access plus alert acknowledgement and automation actions. |
| Admin | Operator access plus server creation, editing, activation, and deactivation. |
