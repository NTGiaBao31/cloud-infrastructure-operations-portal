from app.blueprints.alerts import bp as alerts_bp
from app.blueprints.audit import bp as audit_bp
from app.blueprints.auth import bp as auth_bp
from app.blueprints.automation import bp as automation_bp
from app.blueprints.dashboard import bp as dashboard_bp
from app.blueprints.servers import bp as servers_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(servers_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(automation_bp)
    app.register_blueprint(audit_bp)
