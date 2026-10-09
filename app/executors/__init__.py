from app.executors.ansible import AnsibleRunnerExecutor
from app.executors.mock import MockExecutor
from app.executors.powershell import PowerShellExecutor
from app.executors.shell import ShellExecutor

EXECUTORS = {
    "mock": MockExecutor,
    "ansible": AnsibleRunnerExecutor,
    "powershell": PowerShellExecutor,
    "shell": ShellExecutor,
}


def get_executor(name):
    return EXECUTORS[name]
