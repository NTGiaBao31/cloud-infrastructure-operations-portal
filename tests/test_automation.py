from sqlalchemy import func, select

from app.executors.ansible import AnsibleRunnerExecutor
from app.executors.base import ExecutionResult
from app.executors.powershell import PowerShellExecutor
from app.executors.shell import ShellExecutor
from app.extensions import db
from app.models import AutomationJob, Server, User, utcnow
from app.services.automation import AutomationRejected, dispatch, enqueue_job, scrub_output, validate_parameters
from tests.conftest import login, post_csrf


def test_mock_job_reaches_success_and_failure(seeded):
    class Probe:
        seen = None

        def execute(self, job, server, action_definition):
            Probe.seen = job.status
            return ExecutionResult(True, 0, "probe ok", utcnow(), utcnow())

    with seeded.app_context():
        operator = db.session.scalar(select(User).where(User.username == "operator"))
        server = db.session.scalar(select(Server).where(Server.name == "web-01"))
        original = seeded.config["AUTOMATION_EXECUTOR"]
        seeded.config["AUTOMATION_EXECUTOR"] = "mock"
        import app.services.automation as automation_service

        previous = automation_service.get_executor
        automation_service.get_executor = lambda name: Probe
        try:
            job = enqueue_job(
                server_id=server.id,
                action_key="restart_service",
                parameters={"service_name": "nginx", "simulate": "success"},
                trigger_source="manual",
                requested_by=operator.id,
            )
            assert job.status == "queued"
            finished = dispatch(job.id, actor=operator)
        finally:
            automation_service.get_executor = previous
            seeded.config["AUTOMATION_EXECUTOR"] = original
        assert Probe.seen == "running"
        assert finished.status == "succeeded"
        assert finished.exit_code == 0

        failed = enqueue_job(
            server_id=server.id,
            action_key="restart_service",
            parameters={"service_name": "nginx", "simulate": "fail"},
            trigger_source="manual",
            requested_by=operator.id,
        )
        failed = dispatch(failed.id, actor=operator)
        assert failed.status == "failed"
        assert failed.exit_code == 1


def test_allow_list_rejects_commands_and_unknown_actions():
    for action_key, parameters in (
        ("restart_service", {"service_name": "nginx", "command": "id"}),
        ("restart_service", {"service_name": "nginx", "playbook": "automation-ansible"}),
        ("rm-rf", {"service_name": "nginx"}),
        ("automation/ansible/playbooks/restart_service.yml", {"service_name": "nginx"}),
    ):
        try:
            validate_parameters(action_key, parameters)
        except AutomationRejected:
            continue
        raise AssertionError(action_key)


def test_http_rejects_raw_command_and_playbook_path(seeded, client):
    login(client, "operator")
    with seeded.app_context():
        server_id = db.session.scalar(select(Server.id).where(Server.name == "web-01"))
        before = db.session.scalar(select(func.count()).select_from(AutomationJob))
    rejected_command = post_csrf(
        client,
        "/automation/jobs",
        {
            "server_id": str(server_id),
            "action_key": "restart_service",
            "service_name": "nginx",
            "command": "id",
            "simulate": "success",
        },
        page="/automation/",
    )
    rejected_action = post_csrf(
        client,
        "/automation/jobs",
        {
            "server_id": str(server_id),
            "action_key": "automation/ansible/playbooks/restart_service.yml",
            "service_name": "nginx",
            "simulate": "success",
        },
        page="/automation/",
    )
    assert rejected_command.status_code == 400
    assert rejected_action.status_code == 400
    with seeded.app_context():
        db.session.expire_all()
        assert db.session.scalar(select(func.count()).select_from(AutomationJob)) == before


def test_output_is_scrubbed_and_truncated(seeded):
    class SecretExecutor:
        def execute(self, job, server, action_definition):
            output = "password=hunter2\nall good\nAuthorization: Bearer abc\n" + ("x" * 50)
            return ExecutionResult(True, 0, output, utcnow(), utcnow())

    with seeded.app_context():
        seeded.config["JOB_OUTPUT_MAX_CHARS"] = 30
        operator = db.session.scalar(select(User).where(User.username == "operator"))
        server = db.session.scalar(select(Server).where(Server.name == "web-01"))
        import app.services.automation as automation_service

        previous = automation_service.get_executor
        automation_service.get_executor = lambda name: SecretExecutor
        try:
            job = enqueue_job(
                server_id=server.id,
                action_key="restart_container",
                parameters={"container_name": "worker"},
                trigger_source="manual",
                requested_by=operator.id,
            )
            finished = dispatch(job.id, actor=operator)
        finally:
            automation_service.get_executor = previous
        assert "hunter2" not in finished.output_excerpt
        assert "[redacted]" in finished.output_excerpt
        assert "all good" in finished.output_excerpt
        assert finished.output_excerpt.endswith("[truncated]")
        assert scrub_output("token=abc", 100) == "[redacted]"


def test_future_executors_do_not_run_real_commands():
    for executor in (AnsibleRunnerExecutor(), PowerShellExecutor(), ShellExecutor()):
        result = executor.execute(None, None, None)
        assert result.success is False
        assert "disabled" in result.output.lower()
