from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, Empresa
from app.roles import solo_admin
from app.security import obtener_ip_cliente

empresa_bp = Blueprint(
    'empresa',
    __name__,
    url_prefix='/empresa'
)

# ==========================================
# CONFIGURACION EMPRESA
# ==========================================
@empresa_bp.route('/configuracion', methods=['GET', 'POST'])
@login_required
@solo_admin
def configuracion_empresa():
    empresa = current_user.empresa
    ip_actual = obtener_ip_cliente()
    # 🔐 Estado de seguridad por IP
    seguridad_activa = bool(empresa.ip_publica or empresa.ip_rango)


    if request.method == 'POST':
        nombre = request.form.get('nombre')
        ip_publica = request.form.get('ip_publica')
        ip_rango = request.form.get('ip_rango')
        empresa.nombre = nombre
        empresa.ip_publica = ip_publica or None
        empresa.ip_rango = ip_rango or None

        db.session.commit()
        flash('Configuración de empresa actualizada correctamente', 'success')
        return redirect(url_for('empresa.configuracion_empresa'))

    return render_template('empresa_config.html', empresa=empresa, ip_actual=ip_actual, seguridad_activa=seguridad_activa)
