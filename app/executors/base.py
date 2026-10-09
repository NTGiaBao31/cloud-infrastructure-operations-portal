from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExecutionResult:
    success: bool
    exit_code: int
    output: str
    started_at: datetime
    finished_at: datetime


class AutomationExecutor(ABC):
    @abstractmethod
    def execute(self, job, server, action_definition):
        """Run one allow-listed action and return a bounded result."""
