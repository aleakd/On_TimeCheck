from flask import Blueprint, render_template, session, redirect, url_for, abort, flash
from functools import wraps
from app.models import Empresa, db

superadmin_bp = Blueprint(
    "superadmin",
    __name__,
    url_prefix="/control-interno-otc-4839"
)

# 🔐 Decorador exclusivo superadmin
def solo_superadmin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("superadmin"):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# ==============================
# PANEL PRINCIPAL
# ==============================
@superadmin_bp.route("/")
@solo_superadmin
def panel():
    empresas = Empresa.query.order_by(Empresa.created_at.desc()).all()
    return render_template("superadmin_panel.html", empresas=empresas)


# ==============================
# ACTIVAR / DESACTIVAR EMPRESA
# ==============================
@superadmin_bp.route("/toggle/<int:id>")
@solo_superadmin
def toggle_empresa(id):

    empresa = Empresa.query.get_or_404(id)
    empresa.activa = not empresa.activa
    db.session.commit()

    estado = "activada" if empresa.activa else "desactivada"
    flash(f"Empresa {estado} correctamente", "success")

    return redirect(url_for("superadmin.panel"))