import json

from app.executors.base import AutomationExecutor, ExecutionResult
from app.models import utcnow


class MockExecutor(AutomationExecutor):
    """Simulates success or failure and does not touch the target machine."""

    def execute(self, job, server, action_definition):
        started = utcnow()
        try:
            parameters = json.loads(job.parameters_json or "{}")
        except json.JSONDecodeError:
            parameters = {}
        finished = utcnow()
        name = getattr(server, "name", "server")
        if parameters.get("simulate") == "fail":
            return ExecutionResult(
                False,
                1,
                f"Mock executor simulated failure for {action_definition.key} on {name}.",
                started,
                finished,
            )
        return ExecutionResult(
            True,
            0,
            f"Mock executor completed {action_definition.key} on {name}.",
            started,
            finished,
        )
