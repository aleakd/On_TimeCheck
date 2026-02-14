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
        if modo_empleado:
            empleado_id = current_user.empleado_id
        else:
            empleado_id = request.form.get('empleado_id')

        tipo = request.form.get('tipo')
        actividad = request.form.get('actividad')

        if not empleado_id or tipo not in ['INGRESO', 'SALIDA']:
            flash('❌ Datos inválidos', 'danger')
            return redirect(url_for('asistencias.marcar_asistencia'))

        if tipo == 'INGRESO' and not actividad:
            flash('⚠️ Debe seleccionar una actividad para el INGRESO', 'warning')
            return redirect(url_for('asistencias.marcar_asistencia'))

        # 🔒 última asistencia segura por empresa
        ultima = (
            asistencias_empresa()
            .filter_by(empleado_id=empleado_id)
            .order_by(Asistencia.fecha_hora.desc())
            .first()
        )

        if ultima:
            if ultima.tipo == 'INGRESO' and tipo == 'INGRESO':
                flash('❌ El empleado ya tiene un INGRESO activo', 'warning')
                return redirect(url_for('asistencias.marcar_asistencia'))

            if ultima.tipo == 'SALIDA' and tipo == 'SALIDA':
                flash('❌ No puede marcar dos SALIDAS seguidas', 'warning')
                return redirect(url_for('asistencias.marcar_asistencia'))
        else:
            if tipo == 'SALIDA':
                flash('❌ No se puede marcar SALIDA sin un INGRESO previo', 'warning')
                return redirect(url_for('asistencias.marcar_asistencia'))

        asistencia = Asistencia(
            empleado_id=empleado_id,
            empresa_id=current_user.empresa_id,
            tipo=tipo,
            actividad=actividad if tipo == 'INGRESO' else None,
            fecha_hora=datetime.now()
        )

        db.session.add(asistencia)
        db.session.commit()
        empleado = Empleado.query.get(empleado_id)

        registrar_evento(
            accion="CREAR",
            entidad="ASISTENCIA",
            descripcion=f"{tipo} | {empleado.apellido}, {empleado.nombre} | Actividad: {actividad or '-'}"
        )

        flash('✅ Asistencia registrada correctamente', 'success')
        return redirect(url_for('asistencias.marcar_asistencia'))

    return render_template(
        'asistencias.html',
        empleados=empleados,
        asistencias_hoy=asistencias_hoy
    )


# =========================
# REPORTE DIARIO POR BLOQUES
# =========================
@asistencias_bp.route('/reporte-diario')
@login_required
@requiere_ip_empresa
def reporte_diario_bloques():

    hoy = datetime.now().date()

    asistencias = (
        asistencias_empresa()
        .join(Empleado)
        .filter(db.func.date(Asistencia.fecha_hora) == hoy)
        .order_by(Empleado.apellido, Asistencia.fecha_hora)
        .all()
    )

    registros_por_empleado = defaultdict(list)
    for a in asistencias:
        registros_por_empleado[a.empleado].append(a)

    bloques = []

    for empleado, registros in registros_por_empleado.items():
        bloque_actual = None

        for r in registros:
            if r.tipo == 'INGRESO':
                bloque_actual = {
                    'empleado': empleado,
                    'ingreso': r.fecha_hora,
                    'salida': None,
                    'horas': '00:00',
                    'estado': 'EN CURSO'
                }

            elif r.tipo == 'SALIDA' and bloque_actual:
                total_segundos = (r.fecha_hora - bloque_actual['ingreso']).total_seconds()
                horas = int(total_segundos // 3600)
                minutos = int((total_segundos % 3600) // 60)

                bloque_actual.update({
                    'salida': r.fecha_hora,
                    'horas': f'{horas:02d}:{minutos:02d}',
                    'estado': 'OK'
                })

                bloques.append(bloque_actual)
                bloque_actual = None

        if bloque_actual:
            bloques.append(bloque_actual)

    return render_template(
        'reporte_diario_bloques.html',
        bloques=bloques,
        fecha=hoy
    )
