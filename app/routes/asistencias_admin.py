from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Asistencia, Empleado, db
from app.roles import admin_o_supervisor
from app.multitenant import asistencias_empresa
from datetime import datetime
from app.audit import registrar_evento

asistencias_admin_bp = Blueprint(
    'asistencias_admin',
    __name__,
    url_prefix='/asistencias-admin'
)

# ==========================================
# LISTADO GENERAL DE ASISTENCIAS
# ==========================================
@asistencias_admin_bp.route('/')
@login_required
@admin_o_supervisor
def listado():

    asistencias = (
        asistencias_empresa()
        .join(Empleado)
        .order_by(Asistencia.fecha_hora.desc())
        .limit(200)
        .all()
    )

    return render_template(
        'asistencias_admin_list.html',
        asistencias=asistencias
    )


# ==========================================
# ELIMINAR ASISTENCIA
# ==========================================
@asistencias_admin_bp.route('/eliminar/<int:id>')
@login_required
@admin_o_supervisor
def eliminar(id):

    asistencia = asistencias_empresa().filter_by(id=id).first_or_404()

    db.session.delete(asistencia)
    db.session.commit()

    # ==============================
    # 🧾 AUDITORÍA
    # ==============================
    empleado = Empleado.query.get(id)
    registrar_evento(
        accion="ELIMINAR",
        entidad="ASISTENCIA",
        descripcion=f"{asistencia.empleado_id} | {asistencia.tipo}"

    )

    flash("Asistencia eliminada correctamente", "success")
    return redirect(url_for('asistencias_admin.listado'))


# ==========================================
# EDITAR ASISTENCIA
# ==========================================
@asistencias_admin_bp.route('/editar/<int:id>', methods=['GET','POST'])
@login_required
@admin_o_supervisor
def editar(id):

    asistencia = asistencias_empresa().filter_by(id=id).first_or_404()

    if request.method == 'POST':

        tipo = request.form.get('tipo')
        actividad = request.form.get('actividad')
        fecha_hora = request.form.get('fecha_hora')

        asistencia.tipo = tipo
        asistencia.actividad = actividad if tipo == 'INGRESO' else None
        asistencia.fecha_hora = datetime.strptime(fecha_hora, "%Y-%m-%dT%H:%M")

        db.session.commit()
        flash("Asistencia actualizada", "success")

        return redirect(url_for('asistencias_admin.listado'))

    return render_template(
        'asistencia_edit.html',
        asistencia=asistencia
    )
