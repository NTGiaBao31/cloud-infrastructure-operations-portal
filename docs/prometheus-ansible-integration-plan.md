# Prometheus and Ansible Integration Plan

## Current State

- Prometheus metrics and alerts use an HTTP adapter configured through `PROMETHEUS_*` environment variables.
- Alert synchronisation is started manually with `flask --app wsgi sync-prometheus-alerts`; no scheduler is included.
- Automation defaults to `AUTOMATION_EXECUTOR=mock` and records mock results safely.
- Three allow-listed Ansible playbooks exist for service restart, container restart, and dry-run disk cleanup. The Ansible executor intentionally does not launch processes.

## Prometheus Integration

1. Deploy Prometheus and node exporters, then configure scrape targets to match each server's `monitoring_target`, hostname, or IP address.
2. Create alert rules with `severity` and `instance` labels. Use the supported remediation alert names: `service_down`, `container_down`, and `disk_high`.
3. Set `PROMETHEUS_BASE_URL`, TLS verification, and an optional bearer token in deployment secrets; never commit tokens.
4. Run `sync-prometheus-alerts` with a scheduler at a five-minute interval initially.
5. Verify dashboard metrics, alert create/update/resolve behaviour, and safe operation when Prometheus is unavailable.

## Ansible Integration

1. Install and pin `ansible-runner`; create a private Ansible data directory outside the repository or exclude it from source control.
2. Generate inventory from `automation_group`; keep SSH keys, WinRM credentials, and vault passwords in a secret manager or Ansible Vault.
3. Replace the placeholder executor with an `ansible-runner` call mapping each existing action to its fixed playbook.
4. Pass only validated action parameters as extra variables; continue rejecting commands, scripts, shells, and arbitrary playbook paths.
5. Enforce target identity, timeout, result capture, output redaction, and audit logging before setting `AUTOMATION_EXECUTOR=ansible`.
6. Keep `AUTO_REMEDIATION_ENABLED=false` until manual staging runs pass; enable it only for approved alerts and a limited inventory first.

## Acceptance Checks

- Prometheus failures degrade gracefully without breaking dashboard access.
- Scheduled sync imports, updates, and resolves alerts without duplicates.
- Each approved playbook succeeds against staging; viewers cannot run actions and every execution is audited.
- Invalid playbook paths, shell commands, credentials, and unapproved parameters are rejected.
- Failed Ansible jobs store a failed status and redacted output without secrets.

## Rollout and Rollback

- Roll out in `mock` mode, then Ansible staging, then limited production after reviewing logs and audit entries.
- Roll back by setting `AUTOMATION_EXECUTOR=mock` and `AUTO_REMEDIATION_ENABLED=false`; operational history remains intact.
