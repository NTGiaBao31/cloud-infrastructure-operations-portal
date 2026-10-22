import os
from datetime import timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import text

from app.config import ROOT, build_config
from app.extensions import csrf, db, login_manager, migrate
from app.presentation import badge_class

PUBLIC_ENDPOINTS = {"healthz", "auth.login", "static", "index", "webhooks.alertmanager"}


def create_app(test_config=None):
    load_dotenv(override=False)
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(build_config())
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db, directory=str(ROOT / "migrations"), render_as_batch=True)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app import models

    @login_manager.user_loader
    def load_user(user_id):
        user = db.session.get(models.User, int(user_id))
        if user is None or not user.is_active:
            return None
        return user

    from app.blueprints import register_blueprints
    from app.cli import register_cli

    register_blueprints(app)
    register_cli(app)

    @app.get("/healthz")
    def healthz():
        try:
            db.session.execute(text("SELECT 1"))
            database = "ok"
        except Exception:
            database = "error"
        body = {"status": "ok" if database == "ok" else "degraded", "database": database}
        return jsonify(body), 200 if database == "ok" else 503

    @app.get("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("auth.login"))

    @app.before_request
    def require_login():
        if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint is None:
            return None
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))
        return None

    @app.template_filter("dt")
    def format_dt(value):
        if not value:
            return "—"
        if getattr(value, "tzinfo", None) is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value.strftime("%Y-%m-%d %H:%M UTC")

    @app.context_processor
    def inject_ui():
        return {"badge_class": badge_class, "grafana_url": app.config.get("GRAFANA_BASE_URL", "")}

    @app.errorhandler(400)
    def bad_request(_exc):
        return render_template("errors/400.html"), 400

    @app.errorhandler(403)
    def forbidden(_exc):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def missing(_exc):
        return render_template("errors/404.html"), 404

    return app
