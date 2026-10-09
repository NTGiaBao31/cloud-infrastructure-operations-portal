from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import select

from app.extensions import db
from app.forms import LoginForm
from app.models import User, utcnow
from app.services.audit import record

bp = Blueprint("auth", __name__)


def safe_next(target):
    if not target or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return url_for("dashboard.index")
    return target


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(select(User).where(User.username == form.username.data.strip()))
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password.", "danger")
        elif not user.is_active:
            flash("Account is inactive.", "danger")
        else:
            user.last_login_at = utcnow()
            db.session.commit()
            login_user(user)
            record("auth.login", "user", user.id, {})
            return redirect(safe_next(request.args.get("next")))
    return render_template("login.html", form=form)


@bp.post("/logout")
def logout():
    user_id = current_user.id if current_user.is_authenticated else None
    logout_user()
    if user_id is not None:
        record("auth.logout", "user", user_id, {}, user_id=user_id)
    return redirect(url_for("auth.login"))
