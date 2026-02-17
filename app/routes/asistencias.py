from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, Empleado, Asistencia
from app.multitenant import empleados_empresa, asistencias_empresa
from datetime import datetime

from collections import defaultdict
from app.security import requiere_ip_empresa
from app.audit import registrar_evento



asistencias_bp = Blueprint(
    'asistencias',
    __name__,
    url_prefix='/asistencias'
)

# =========================
# MARCAR ASISTENCIA
# =========================
@asistencias_bp.route('/', methods=['GET', 'POST'])
@login_required
@requiere_ip_empresa
def marcar_asistencia():
    # 👇 detectar si es usuario empleado
    modo_empleado = current_user.rol == 'empleado'
    # 👇 si es empleado solo puede verse a sí mismo
    if modo_empleado:
        empleados = [current_user.empleado]
    else:
        empleados = empleados_empresa().filter_by(activo=True) \
            .order_by(Empleado.apellido).all()

    hoy = datetime.now().date()
    asistencias_hoy = (
        asistencias_empresa()
        .join(Empleado)
        .filter(db.func.date(Asistencia.fecha_hora) == hoy)
        .order_by(Asistencia.fecha_hora.desc())
        .all()
    )

    if request.method == 'POST':
        if request.method == 'POST':

            # ==============================
            # DATOS FORM
            # ==============================
            if modo_empleado:
                empleado_id = current_user.empleado_id
            else:
                empleado_id = request.form.get('empleado_id')

            tipo = request.form.get('tipo')
            actividad = request.form.get('actividad')
            fecha_hora = datetime.utcnow()

            # 👇 NUEVO — CAMPOS MANUALES ADMIN
            fecha_manual = request.form.get("fecha_manual")
            hora_manual = request.form.get("hora_manual")

            if not empleado_id or tipo not in ['INGRESO', 'SALIDA']:
                flash('❌ Datos inválidos', 'danger')
                return redirect(url_for('asistencias.marcar_asistencia'))

            if tipo == 'INGRESO' and not actividad:
                flash('⚠️ Debe seleccionar una actividad para el INGRESO', 'warning')
                return redirect(url_for('asistencias.marcar_asistencia'))

            # ==============================
            # ⏰ FECHA INTELIGENTE
            # ==============================



            # ==============================
            # 🔒 VALIDACIÓN TEMPORAL CORRECTA
            # busca la última asistencia ANTERIOR a la que estoy cargando
            # ==============================
            ultima = (
                asistencias_empresa()
                .filter(
                    Asistencia.empleado_id == empleado_id,
                    Asistencia.fecha_hora < fecha_hora
                )
                .order_by(Asistencia.fecha_hora.desc())
                .first()
            )

            if ultima:
                if ultima.tipo == 'INGRESO' and tipo == 'INGRESO':
                    flash('❌ El empleado ya tenía un INGRESO activo en ese momento', 'warning')
                    return redirect(url_for('asistencias.marcar_asistencia'))

                if ultima.tipo == 'SALIDA' and tipo == 'SALIDA':
                    flash('❌ No puede haber dos SALIDAS seguidas en esa fecha', 'warning')
                    return redirect(url_for('asistencias.marcar_asistencia'))
            else:
                if tipo == 'SALIDA':
                    flash('❌ No puede cargar una SALIDA sin un INGRESO previo', 'warning')
                    return redirect(url_for('asistencias.marcar_asistencia'))

            # ==============================
            # 💾 GUARDAR
            # ==============================
            asistencia = Asistencia(
                empleado_id=empleado_id,
                empresa_id=current_user.empresa_id,
                tipo=tipo,
                actividad=actividad if tipo == 'INGRESO' else None
            )

            db.session.add(asistencia)
            db.session.commit()

            # ==============================
            # 🧾 AUDITORÍA
            # ==============================
            empleado = Empleado.query.get(empleado_id)

            registrar_evento(
                accion="CREAR",
                entidad="ASISTENCIA",
                descripcion=f"{tipo} | {empleado.apellido}, {empleado.nombre}"

            )

            flash('✅ Asistencia registrada correctamente', 'success')
            return redirect(url_for('asistencias.marcar_asistencia'))

    return render_template(
        'asistencias.html',
        empleados=empleados,
        asistencias_hoy=asistencias_hoy,

    )


