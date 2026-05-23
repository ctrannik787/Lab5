from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user, login_required


def can_create_user(user):
    return user.is_authenticated and user.is_admin


def can_delete_user(user):
    return user.is_authenticated and user.is_admin


def can_view_user(user, target_user):
    if not user.is_authenticated:
        return False
    return user.is_admin or user.id == target_user.id


def can_edit_user(user, target_user):
    if not user.is_authenticated:
        return False
    return user.is_admin or user.id == target_user.id


def can_view_logs(user):
    return user.is_authenticated and (user.is_admin or user.is_regular_user)


RIGHT_CHECKS = {
    "create_user": lambda user, **_: can_create_user(user),
    "delete_user": lambda user, **_: can_delete_user(user),
    "view_user": lambda user, target_user=None, **_: target_user is not None and can_view_user(user, target_user),
    "edit_user": lambda user, target_user=None, **_: target_user is not None and can_edit_user(user, target_user),
    "view_logs": lambda user, **_: can_view_logs(user),
}


def check_rights(right, resolver=None):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(*args, **kwargs):
            context = resolver(*args, **kwargs) if resolver is not None else {}
            checker = RIGHT_CHECKS[right]
            if not checker(current_user, **context):
                flash("У вас недостаточно прав для доступа к данной странице.", "danger")
                return redirect(url_for("main.index"))
            return view_func(*args, **kwargs)

        return wrapper

    return decorator
