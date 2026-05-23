from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import SQLAlchemyError

from auth import can_create_user, can_delete_user, can_edit_user, can_view_user, check_rights
from extensions import db
from models import Role, User
from validators import form_value, validate_login, validate_password, validate_required

main_bp = Blueprint("main", __name__)


def user_or_404(user_id):
    return db.get_or_404(User, user_id)


def role_choices():
    return Role.query.order_by(Role.name).all()


def collect_user_form(include_credentials):
    data = {
        "last_name": form_value(request.form, "last_name"),
        "first_name": form_value(request.form, "first_name"),
        "middle_name": form_value(request.form, "middle_name"),
        "role_id": request.form.get("role_id") or None,
    }
    if include_credentials:
        data["login"] = form_value(request.form, "login")
        data["password"] = request.form.get("password") or ""
    return data


def validate_user_form(data, include_credentials):
    errors = {
        "last_name": validate_required(data.get("last_name")),
        "first_name": validate_required(data.get("first_name")),
    }
    if include_credentials:
        errors["login"] = validate_login(data.get("login"))
        errors["password"] = validate_password(data.get("password"))
    return {field: messages for field, messages in errors.items() if messages}


def apply_user_form(user, data, include_credentials, allow_role=True):
    user.last_name = data["last_name"]
    user.first_name = data["first_name"]
    user.middle_name = data["middle_name"]
    if allow_role:
        user.role_id = int(data["role_id"]) if data["role_id"] else None
    if include_credentials:
        user.login = data["login"]
        user.set_password(data["password"])


@main_bp.app_context_processor
def inject_permissions():
    return {
        "can_create_user": can_create_user,
        "can_delete_user": can_delete_user,
        "can_edit_user": can_edit_user,
        "can_view_user": can_view_user,
    }


@main_bp.route("/")
def index():
    users = User.query.order_by(User.id).all()
    return render_template("index.html", users=users)


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        login_value = form_value(request.form, "login")
        password = request.form.get("password") or ""
        user = User.query.filter_by(login=login_value).first()

        if user is None or not user.check_password(password):
            flash("Неверный логин или пароль.", "danger")
            return render_template("login.html", login=login_value)

        login_user(user)
        flash("Вы успешно вошли в систему.", "success")
        return redirect(url_for("main.index"))

    return render_template("login.html")


@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли из системы.", "success")
    return redirect(url_for("main.index"))


@main_bp.route("/users/<int:user_id>")
@check_rights("view_user", resolver=lambda user_id: {"target_user": user_or_404(user_id)})
def view_user(user_id):
    user = user_or_404(user_id)
    return render_template("user_view.html", user=user)


@main_bp.route("/users/create", methods=["GET", "POST"])
@check_rights("create_user")
def create_user():
    data = collect_user_form(include_credentials=True) if request.method == "POST" else {}
    errors = {}

    if request.method == "POST":
        errors = validate_user_form(data, include_credentials=True)
        if not errors:
            try:
                user = User()
                apply_user_form(user, data, include_credentials=True)
                db.session.add(user)
                db.session.commit()
                flash("Пользователь успешно создан.", "success")
                return redirect(url_for("main.index"))
            except SQLAlchemyError as exc:
                db.session.rollback()
                flash(f"Ошибка при создании пользователя: {exc.__class__.__name__}.", "danger")
        else:
            flash("Проверьте корректность заполнения формы.", "danger")

    return render_template("user_form.html", user=None, data=data, errors=errors, roles=role_choices(), mode="create")


@main_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@check_rights("edit_user", resolver=lambda user_id: {"target_user": user_or_404(user_id)})
def edit_user(user_id):
    user = user_or_404(user_id)
    allow_role = current_user.is_admin
    data = collect_user_form(include_credentials=False) if request.method == "POST" else {
        "last_name": user.last_name or "",
        "first_name": user.first_name or "",
        "middle_name": user.middle_name or "",
        "role_id": str(user.role_id or ""),
    }
    errors = {}

    if request.method == "POST":
        errors = validate_user_form(data, include_credentials=False)
        if not errors:
            try:
                apply_user_form(user, data, include_credentials=False, allow_role=allow_role)
                db.session.commit()
                flash("Пользователь успешно обновлён.", "success")
                return redirect(url_for("main.index"))
            except SQLAlchemyError as exc:
                db.session.rollback()
                flash(f"Ошибка при обновлении пользователя: {exc.__class__.__name__}.", "danger")
        else:
            flash("Проверьте корректность заполнения формы.", "danger")

    return render_template(
        "user_form.html",
        user=user,
        data=data,
        errors=errors,
        roles=role_choices(),
        mode="edit",
        allow_role=allow_role,
    )


@main_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@check_rights("delete_user")
def delete_user(user_id):
    user = user_or_404(user_id)
    try:
        db.session.delete(user)
        db.session.commit()
        flash("Пользователь успешно удалён.", "success")
    except SQLAlchemyError as exc:
        db.session.rollback()
        flash(f"Ошибка при удалении пользователя: {exc.__class__.__name__}.", "danger")
    return redirect(url_for("main.index"))


@main_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    errors = {}
    if request.method == "POST":
        old_password = request.form.get("old_password") or ""
        new_password = request.form.get("new_password") or ""
        repeat_password = request.form.get("repeat_password") or ""

        if not current_user.check_password(old_password):
            errors["old_password"] = ["Старый пароль указан неверно."]
        new_password_errors = validate_password(new_password)
        if new_password_errors:
            errors["new_password"] = new_password_errors
        if new_password != repeat_password:
            errors["repeat_password"] = ["Новые пароли не совпадают."]

        if not errors:
            current_user.set_password(new_password)
            db.session.commit()
            flash("Пароль успешно изменён.", "success")
            return redirect(url_for("main.index"))

        flash("Проверьте корректность заполнения формы.", "danger")

    return render_template("change_password.html", errors=errors)
