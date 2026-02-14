from flask import Blueprint, render_template
from flask_login import login_required
from app.roles import solo_admin
from app.models import AuditLog
from flask_login import current_user
from collections import Counter

auditoria_bp = Blueprint(
    'auditoria',
    __name__,
    url_prefix='/auditoria'
)

# ==========================================
# LISTADO + ESTADISTICAS AUDITORIA
# ==========================================
@auditoria_bp.route('/')
@login_required
@solo_admin
def auditoria():

    # 🔐 logs solo de la empresa del usuario
    logs = (
        AuditLog.query
        .filter_by(empresa_id=current_user.empresa_id)
        .order_by(AuditLog.created_at.desc())
        .limit(200)
        .all()
    )

    # ======================================
    # 📊 GENERAR DATOS PARA EL GRÁFICO
    # ======================================
    acciones = [log.accion for log in logs]
    conteo = Counter(acciones)

    chart_labels = list(conteo.keys())
    chart_data = list(conteo.values())

    return render_template(
        "auditoria.html",
        logs=logs,
        chart_labels=chart_labels,
        chart_data=chart_data
    )
