from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.authz import roles_required
from app.extensions import db
from app.forms import ServerForm
from app.models import Server, utcnow
from app.services.audit import record
from app.validation import blank_to_none

bp = Blueprint("servers", __name__, url_prefix="/servers")

STATUS_FILTERS = {"online", "warning", "down", "maintenance", "unknown"}
OS_FILTERS = {"linux", "windows"}


def _apply_form(server, form):
    server.name = form.name.data.strip()
    server.hostname = form.hostname.data.strip()
    server.ip_address = form.ip_address.data.strip()
    server.environment = form.environment.data.strip()
    server.os_type = form.os_type.data
    server.status = form.status.data
    server.monitoring_target = blank_to_none(form.monitoring_target.data)
    server.automation_group = blank_to_none(form.automation_group.data)
    server.azure_resource_id = blank_to_none(form.azure_resource_id.data)
    server.updated_at = utcnow()


def _fill_form(form, server):
    form.name.data = server.name
    form.hostname.data = server.hostname
    form.ip_address.data = server.ip_address
    form.environment.data = server.environment
    form.os_type.data = server.os_type
    form.status.data = server.status
    form.monitoring_target.data = server.monitoring_target or ""
    form.automation_group.data = server.automation_group or ""
    form.azure_resource_id.data = server.azure_resource_id or ""


@bp.get("/")
def index():
    status = request.args.get("status", "")
    environment = request.args.get("environment", "")
    os_type = request.args.get("os_type", "")
    if status not in STATUS_FILTERS:
        status = ""
    if os_type not in OS_FILTERS:
        os_type = ""
    if environment and not environment.replace("-", "").replace("_", "").isalnum():
        environment = ""
    query = select(Server).order_by(Server.name)
    if status:
        query = query.where(Server.status == status)
    if environment:
        query = query.where(Server.environment == environment)
    if os_type:
        query = query.where(Server.os_type == os_type)
    servers = db.session.scalars(query).all()
    return render_template(
        "servers/list.html",
        servers=servers,
        status=status,
        environment=environment,
        os_type=os_type,
    )


@bp.get("/<int:server_id>")
def detail(server_id):
    server = db.session.get(Server, server_id)
    if server is None:
        abort(404)
    alerts = sorted(server.alerts, key=lambda alert: alert.created_at, reverse=True)
    jobs = sorted(server.jobs, key=lambda job: job.created_at, reverse=True)
    return render_template("servers/detail.html", server=server, alerts=alerts, jobs=jobs)


@bp.route("/new", methods=["GET", "POST"])
@roles_required("admin")
def create():
    form = ServerForm()
    if form.validate_on_submit():
        server = Server(name=form.name.data.strip(), created_at=utcnow(), is_active=True)
        _apply_form(server, form)
        db.session.add(server)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("A server with that name already exists.", "danger")
            return render_template("servers/form.html", form=form, title="Add server")
        record("server.create", "server", server.id, {"name": server.name})
        flash("Server saved.", "success")
        return redirect(url_for("servers.detail", server_id=server.id))
    return render_template("servers/form.html", form=form, title="Add server")


@bp.route("/<int:server_id>/edit", methods=["GET", "POST"])
@roles_required("admin")
def edit(server_id):
    server = db.session.get(Server, server_id)
    if server is None:
        abort(404)
    form = ServerForm()
    if request.method == "GET":
        _fill_form(form, server)
    if form.validate_on_submit():
        _apply_form(server, form)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("A server with that name already exists.", "danger")
            return render_template("servers/form.html", form=form, title="Edit server", server=server)
        record("server.update", "server", server.id, {"name": server.name})
        flash("Server updated.", "success")
        return redirect(url_for("servers.detail", server_id=server.id))
    return render_template("servers/form.html", form=form, title="Edit server", server=server)


@bp.post("/<int:server_id>/deactivate")
@roles_required("admin")
def deactivate(server_id):
    server = db.session.get(Server, server_id)
    if server is None:
        abort(404)
    server.is_active = False
    server.updated_at = utcnow()
    db.session.commit()
    record("server.deactivate", "server", server.id, {"name": server.name}, user_id=current_user.id)
    flash("Server deactivated.", "success")
    return redirect(url_for("servers.detail", server_id=server.id))


@bp.post("/<int:server_id>/activate")
@roles_required("admin")
def activate(server_id):
    server = db.session.get(Server, server_id)
    if server is None:
        abort(404)
    server.is_active = True
    server.updated_at = utcnow()
    db.session.commit()
    record("server.activate", "server", server.id, {"name": server.name}, user_id=current_user.id)
    flash("Server activated.", "success")
    return redirect(url_for("servers.detail", server_id=server.id))
