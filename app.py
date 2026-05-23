import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_login import LoginManager
from extensions import db
from models import Role, User
from routes import main_bp
from reports import reports_bp


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "change-this-secret-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lab5.sqlite3"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager = LoginManager()
    login_manager.login_view = "main.login"
    login_manager.login_message = "Для доступа к этой странице необходимо войти в систему."
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    app.register_blueprint(main_bp)
    app.register_blueprint(reports_bp, url_prefix="/reports")

    with app.app_context():
        db.create_all()
        seed_data()

    return app


def seed_data():
    admin_role = Role.query.filter_by(name="Администратор").first()
    user_role = Role.query.filter_by(name="Пользователь").first()

    if admin_role is None:
        admin_role = Role(name="Администратор", description="Полный доступ к управлению пользователями и журналу посещений.")
        db.session.add(admin_role)

    if user_role is None:
        user_role = Role(name="Пользователь", description="Доступ к собственному профилю, своим данным и своему журналу посещений.")
        db.session.add(user_role)

    db.session.flush()

    if User.query.filter_by(login="admin").first() is None:
        admin = User(
            login="admin",
            last_name="Администратор",
            first_name="Системный",
            middle_name="",
            role_id=admin_role.id,
        )
        admin.set_password("Admin123!")
        db.session.add(admin)

    db.session.commit()


if __name__ == "__main__":
    create_app().run(debug=True, use_reloader=False)
