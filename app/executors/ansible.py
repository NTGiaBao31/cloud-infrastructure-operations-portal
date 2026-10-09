from app.executors.base import AutomationExecutor, ExecutionResult
from app.models import utcnow


class AnsibleRunnerExecutor(AutomationExecutor):
    """Future ansible-runner adapter. This MVP does not spawn a process.

    A later worker can pass private_data_dir, inventory from automation_group,
    the allow-listed playbook, and extravars drawn from the action parameters.
    Secrets stay in the environment, Ansible Vault, or an external store.
    """

    def execute(self, job, server, action_definition):
        now = utcnow()
        return ExecutionResult(
            False,
            1,
            "Real Ansible execution is disabled in MVP.",
            now,
            now,
        )
