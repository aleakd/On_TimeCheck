from flask import Flask
from app.models import db
from flask_login import LoginManager


login_manager = LoginManager()
login_manager.login_view = 'auth.login'


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'on_timecheck_secret'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///on_timecheck.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)


#-------------------------------------------------------------------------------------------------------

    from app.routes.empleados import empleados_bp
    app.register_blueprint(empleados_bp)

    from app.routes.reportes import reportes_bp
    app.register_blueprint(reportes_bp)

    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    from app.routes.asistencias import asistencias_bp
    app.register_blueprint(asistencias_bp)

    from app.routes.debug import debug_bp
    app.register_blueprint(debug_bp)

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.usuarios import usuarios_bp
    app.register_blueprint(usuarios_bp)

    # -------------------------------------------------------------------------------------------------------



    # 🔑 ESTA ES LA CLAVE
    with app.app_context():
        db.create_all()

    return app

