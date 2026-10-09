import json
import re

from flask import abort, current_app

from app.extensions import db
from app.executors import EXECUTORS, get_executor
from app.executors.actions import ACTIONS
from app.models import AutomationJob, Server, utcnow
from app.services.audit import record
from app.validation import TOKEN_RE

REJECTED_PARAMETER_KEYS = {"command", "cmd", "playbook", "script", "shell", "playbook_path"}
SECRET_LINE = re.compile(r"(password|passwd|token|secret|authorization|api[_-]?key)\s*[:=]", re.IGNORECASE)


class AutomationRejected(ValueError):
    pass


def validate_parameters(action_key, parameters):
    if not isinstance(parameters, dict):
        raise AutomationRejected("Invalid parameters.")
    if action_key not in ACTIONS:
        raise AutomationRejected("Action is not allowed.")
    if REJECTED_PARAMETER_KEYS & set(parameters):
        raise AutomationRejected("Parameter is not allowed.")
    action = ACTIONS[action_key]
    allowed = set(action.params) | {"simulate"}
    if action.dry_run:
        allowed.add("dry_run")
    if set(parameters) - allowed:
        raise AutomationRejected("Parameter is not allowed.")
    for value in parameters.values():
        if not isinstance(value, str) or not TOKEN_RE.match(value):
            raise AutomationRejected("Invalid parameter value.")
    if "simulate" in parameters and parameters["simulate"] not in {"fail", "success"}:
        raise AutomationRejected("Invalid parameter value.")
    for key in action.params:
        if not parameters.get(key):
            raise AutomationRejected("Missing parameter.")
    if action.dry_run:
        parameters["dry_run"] = "true"
    return action


def scrub_output(output, limit):
    lines = []
    for line in (output or "").splitlines():
        if SECRET_LINE.search(line) or "bearer " in line.lower():
            lines.append("[redacted]")
        else:
            lines.append(line)
    text = "\n".join(lines)
    if len(text) > limit:
        return text[:limit] + "\n[truncated]"
    return text


def enqueue_job(*, server_id, action_key, parameters, trigger_source, requested_by=None, alert_id=None):
    action = validate_parameters(action_key, parameters)
    server = db.session.get(Server, server_id) if server_id is not None else None
    if server is None or not server.is_active:
        raise AutomationRejected("Server is not available.")
    if trigger_source not in {"manual", "remediation", "system"}:
        raise AutomationRejected("Invalid trigger.")
    executor_name = current_app.config.get("AUTOMATION_EXECUTOR", "mock")
    if executor_name not in EXECUTORS:
        raise AutomationRejected("Unknown executor.")
    job = AutomationJob(
        server_id=server.id,
        alert_id=alert_id,
        requested_by=requested_by,
        trigger_source=trigger_source,
        executor=executor_name,
        action_key=action.key,
        parameters_json=json.dumps(parameters, sort_keys=True),
        status="queued",
        created_at=utcnow(),
    )
    db.session.add(job)
    db.session.commit()
    record(
        "job.request",
        "automation_job",
        job.id,
        {
            "action_key": action.key,
            "trigger_source": trigger_source,
            "alert_id": alert_id,
            "server_id": server.id,
        },
        user_id=requested_by,
    )
    return job


def dispatch(job_id, actor=None):
    job = db.session.get(AutomationJob, job_id)
    if job is None:
        raise AutomationRejected("Job not found.")
    if actor is None:
        if job.trigger_source != "remediation":
            raise AutomationRejected("Not allowed.")
    elif getattr(actor, "role", None) not in {"operator", "admin"}:
        abort(403)
    if job.status != "queued":
        raise AutomationRejected("Job is not queued.")

    def _fail(message):
        now = utcnow()
        job.status = "failed"
        job.exit_code = 1
        job.output_excerpt = scrub_output(message, current_app.config["JOB_OUTPUT_MAX_CHARS"])
        job.started_at = job.started_at or now
        job.finished_at = now
        db.session.commit()
        record(
            "job.result",
            "automation_job",
            job.id,
            {"status": job.status, "exit_code": job.exit_code, "alert_id": job.alert_id},
            user_id=getattr(actor, "id", None),
        )
        return job

    server = db.session.get(Server, job.server_id) if job.server_id else None
    if server is None or not server.is_active:
        return _fail("Server is not available.")
    try:
        parameters = json.loads(job.parameters_json or "{}")
        action = validate_parameters(job.action_key, parameters)
    except (AutomationRejected, json.JSONDecodeError):
        return _fail("Action is not allowed.")
    if job.executor not in EXECUTORS:
        return _fail("Real execution is disabled in MVP.")

    job.parameters_json = json.dumps(parameters, sort_keys=True)
    job.status = "running"
    job.started_at = utcnow()
    db.session.commit()

    result = get_executor(job.executor)().execute(job, server, action)
    job.status = "succeeded" if result.success else "failed"
    job.exit_code = result.exit_code
    job.output_excerpt = scrub_output(result.output, current_app.config["JOB_OUTPUT_MAX_CHARS"])
    job.finished_at = result.finished_at or utcnow()
    db.session.commit()
    record(
        "job.result",
        "automation_job",
        job.id,
        {"status": job.status, "exit_code": job.exit_code, "alert_id": job.alert_id},
        user_id=getattr(actor, "id", None),
    )
    return job


def queue_and_dispatch(*, server_id, action_key, parameters, actor, alert_id=None):
    job = enqueue_job(
        server_id=server_id,
        action_key=action_key,
        parameters=parameters,
        trigger_source="manual",
        requested_by=getattr(actor, "id", None),
        alert_id=alert_id,
    )
    return dispatch(job.id, actor=actor)
