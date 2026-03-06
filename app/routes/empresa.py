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

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()

        if not nombre:
            flash("El nombre de la empresa es obligatorio", "danger")
            return redirect(url_for('empresa.configuracion_empresa'))

        empresa.nombre = nombre
        db.session.commit()

        flash('Configuración de empresa actualizada correctamente', 'success')
        return redirect(url_for('empresa.configuracion_empresa'))

    return render_template(
        'empresa_config.html',
        empresa=empresa,
        ip_actual=ip_actual
    )