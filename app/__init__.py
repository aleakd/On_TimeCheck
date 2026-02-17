from flask import Flask, render_template, g
from app.models import db
from flask_login import LoginManager, current_user
from app.models import Empresa, Asistencia, Usuario, AuditLog
import os
from zoneinfo import ZoneInfo

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'on_timecheck_secret'
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        # Render usa postgres:// y SQLAlchemy necesita postgresql://
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///on_timecheck.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['EXPLAIN_TEMPLATE_LOADING'] = True

    db.init_app(app)
    login_manager.init_app(app)

    # ==========================================
    # 🕒 FILTRO GLOBAL HORA ARGENTINA (CLAVE)
    # ==========================================
    def convertir_a_argentina(fecha):
        if fecha is None:
            return ""
        return fecha.astimezone(ZoneInfo("America/Argentina/Buenos_Aires"))

    app.jinja_env.filters['hora_ar'] = convertir_a_argentina

    # -------------------------------------------------------------------------------------------------------
    from app.routes.empleados import empleados_bp
    app.register_blueprint(empleados_bp)

    from app.routes.reportes import reportes_bp
    app.register_blueprint(reportes_bp)

    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    from app.routes.asistencias import asistencias_bp
    app.register_blueprint(asistencias_bp)

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.usuarios import usuarios_bp
    app.register_blueprint(usuarios_bp)

    from app.routes.empresa import empresa_bp
    app.register_blueprint(empresa_bp)

    from app.routes.auditoria import auditoria_bp
    app.register_blueprint(auditoria_bp)

    # -------------------------------------------------------------------------------------------------------
    # 🔑 CREAR TABLAS SI NO EXISTEN
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
