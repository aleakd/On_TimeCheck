from flask import Flask, render_template, g
from app.models import db
from flask_login import LoginManager,current_user
from app.models import Empresa



login_manager = LoginManager()
login_manager.login_view = 'auth.login'


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'on_timecheck_secret'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///on_timecheck.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)

    # 👇 permitir usar current_user en todos los templates
    @app.context_processor
    def inject_user():
        return dict(current_user=current_user)


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

    from app.routes.empresa import empresa_bp
    app.register_blueprint(empresa_bp)

    # -------------------------------------------------------------------------------------------------------
    # 🔑 ESTA ES LA CLAVE
    with app.app_context():
        db.create_all()

    # ==========================================
    # CARGAR EMPRESA EN CADA REQUEST (MULTITENANT)
    # ==========================================
    @app.before_request
    def cargar_empresa():
        if current_user.is_authenticated:
            g.empresa = Empresa.query.get(current_user.empresa_id)
        else:
            g.empresa = None

    # ==============================
    # PAGINA 403 PERSONALIZADA
    # ==============================
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403






    return app

