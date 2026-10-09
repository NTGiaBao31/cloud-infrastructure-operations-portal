from dataclasses import dataclass


@dataclass(frozen=True)
class ActionDefinition:
    key: str
    playbook: str
    params: tuple[str, ...]
    dry_run: bool = False


ACTIONS = {
    "restart_service": ActionDefinition(
        "restart_service",
        "automation/ansible/playbooks/restart_service.yml",
        ("service_name",),
    ),
    "restart_container": ActionDefinition(
        "restart_container",
        "automation/ansible/playbooks/restart_container.yml",
        ("container_name",),
    ),
    "disk_cleanup": ActionDefinition(
        "disk_cleanup",
        "automation/ansible/playbooks/disk_cleanup.yml",
        ("path",),
        dry_run=True,
    ),
}
