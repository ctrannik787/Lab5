import csv
from io import StringIO

from flask import Blueprint, Response, render_template, request
from flask_login import current_user
from sqlalchemy import func

from auth import check_rights
from extensions import db
from models import User, VisitLog

reports_bp = Blueprint("reports", __name__, template_folder="templates")


@reports_bp.before_app_request
def log_visit():
    if request.endpoint == "static":
        return

    path = request.path[:100]
    user_id = current_user.id if current_user.is_authenticated else None
    db.session.add(VisitLog(path=path, user_id=user_id))
    db.session.commit()


def visible_logs_query():
    query = VisitLog.query
    if not current_user.is_admin:
        query = query.filter(VisitLog.user_id == current_user.id)
    return query


def visitor_name(user):
    return user.full_name if user is not None else "Неаутентифицированный пользователь"


@reports_bp.route("/visits")
@check_rights("view_logs")
def visits():
    page = request.args.get("page", 1, type=int)
    pagination = visible_logs_query().order_by(VisitLog.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template("reports/visits.html", pagination=pagination, logs=pagination.items)


@reports_bp.route("/pages")
@check_rights("view_logs")
def pages_report():
    rows = (
        visible_logs_query()
        .with_entities(VisitLog.path, func.count(VisitLog.id).label("visits_count"))
        .group_by(VisitLog.path)
        .order_by(func.count(VisitLog.id).desc())
        .all()
    )
    return render_template("reports/pages.html", rows=rows)


@reports_bp.route("/pages.csv")
@check_rights("view_logs")
def pages_csv():
    rows = (
        visible_logs_query()
        .with_entities(VisitLog.path, func.count(VisitLog.id).label("visits_count"))
        .group_by(VisitLog.path)
        .order_by(func.count(VisitLog.id).desc())
        .all()
    )
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["№", "Страница", "Количество посещений"])
    for index, row in enumerate(rows, start=1):
        writer.writerow([index, row.path, row.visits_count])
    return csv_response(output.getvalue(), "pages_report.csv")


@reports_bp.route("/users")
@check_rights("view_logs")
def users_report():
    rows = (
        visible_logs_query()
        .outerjoin(User, VisitLog.user_id == User.id)
        .with_entities(User, func.count(VisitLog.id).label("visits_count"))
        .group_by(VisitLog.user_id)
        .order_by(func.count(VisitLog.id).desc())
        .all()
    )
    return render_template("reports/users.html", rows=rows, visitor_name=visitor_name)


@reports_bp.route("/users.csv")
@check_rights("view_logs")
def users_csv():
    rows = (
        visible_logs_query()
        .outerjoin(User, VisitLog.user_id == User.id)
        .with_entities(User, func.count(VisitLog.id).label("visits_count"))
        .group_by(VisitLog.user_id)
        .order_by(func.count(VisitLog.id).desc())
        .all()
    )
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["№", "Пользователь", "Количество посещений"])
    for index, row in enumerate(rows, start=1):
        writer.writerow([index, visitor_name(row[0]), row.visits_count])
    return csv_response(output.getvalue(), "users_report.csv")


def csv_response(content, filename):
    return Response(
        "\ufeff" + content,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
