from app.executors.base import AutomationExecutor, ExecutionResult
from app.models import utcnow


class PowerShellExecutor(AutomationExecutor):
    """Placeholder for a future Windows remoting adapter. No process is started."""

    def execute(self, job, server, action_definition):
        now = utcnow()
        return ExecutionResult(
            False,
            1,
            "Real PowerShell execution is disabled in MVP.",
            now,
            now,
        )
