from app.executors.base import AutomationExecutor, ExecutionResult
from app.models import utcnow


class ShellExecutor(AutomationExecutor):
    """Placeholder for a future shell adapter. No process is started."""

    def execute(self, job, server, action_definition):
        now = utcnow()
        return ExecutionResult(
            False,
            1,
            "Real shell execution is disabled in MVP.",
            now,
            now,
        )
