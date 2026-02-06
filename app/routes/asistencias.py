from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import db, Empleado, Asistencia
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy import extract
#from app.context import get_empresa_activa
from flask_login import login_required, current_user

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
def marcar_asistencia():

    # Empleados activos
    #empresa = get_empresa_activa()

    empleados = (
        Empleado.query
        .filter_by(
            activo=True,
            empresa_id=current_user.empresa_id
        )
        .order_by(Empleado.apellido)
        .all()
    )

    # Asistencias del día
    hoy = datetime.now().date()
    asistencias_hoy = (
        Asistencia.query
        .join(Empleado)
        .filter(
            db.func.date(Asistencia.fecha_hora) == hoy,
            Asistencia.empresa_id == current_user.empresa_id

        )
        .order_by(Asistencia.fecha_hora.desc())
        .all()
    )

    if request.method == 'POST':
        empleado_id = request.form.get('empleado_id')
        tipo = request.form.get('tipo')
        actividad = request.form.get('actividad')

        # Validaciones básicas
        if not empleado_id or tipo not in ['INGRESO', 'SALIDA']:
            flash('❌ Datos inválidos', 'danger')
            return redirect(url_for('asistencias.marcar_asistencia'))

        # Actividad solo obligatoria en INGRESO
        if tipo == 'INGRESO' and not actividad:
            flash('⚠️ Debe seleccionar una actividad para el INGRESO', 'warning')
            return redirect(url_for('asistencias.marcar_asistencia'))

        # Última asistencia del empleado
        ultima = (
            Asistencia.query
            .filter_by(
                empleado_id=empleado_id,
                empresa_id=current_user.empresa_id
            )
            .order_by(Asistencia.fecha_hora.desc())
            .first()
        )

        # Validaciones de secuencia
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

        # Registro válido
        asistencia = Asistencia(
            empleado_id=empleado_id,
            empresa_id=current_user.empresa_id,
            tipo=tipo,
            actividad=actividad if tipo == 'INGRESO' else None,
            fecha_hora=datetime.now()
        )

        db.session.add(asistencia)
        db.session.commit()

        flash('✅ Asistencia registrada correctamente', 'success')
        return redirect(url_for('asistencias.marcar_asistencia'))

    return render_template(
        'asistencias.html',
        empleados=empleados,
        empresa_id=current_user.empresa_id,
        asistencias_hoy=asistencias_hoy
    )


# =========================
# REPORTE DIARIO
# =========================
@asistencias_bp.route('/reporte-diario')
@login_required
def reporte_diario():

    hoy = datetime.now().date()

    #empresa = get_empresa_activa()

    asistencias = (
        Asistencia.query
        .join(Empleado)
        .filter(
            db.func.date(Asistencia.fecha_hora) == hoy,
            Asistencia.empresa_id == current_user.empresa_id

        )
        .order_by(Empleado.apellido, Asistencia.fecha_hora)
        .all()
    )

    # Agrupar por empleado
    reporte = defaultdict(list)
    for a in asistencias:
        reporte[a.empleado].append(a)

    resumen = []

    for empleado, registros in reporte.items():

        ingreso = None
        salida = None
        ultimo_ingreso = None
        total_segundos = 0
        actividad = None

        for r in registros:
            if r.tipo == 'INGRESO':
                ultimo_ingreso = r.fecha_hora
                if not ingreso:
                    ingreso = r.fecha_hora
                    actividad = r.actividad  # actividad del primer ingreso
            elif r.tipo == 'SALIDA' and ultimo_ingreso:
                salida = r.fecha_hora
                total_segundos += (r.fecha_hora - ultimo_ingreso).total_seconds()
                ultimo_ingreso = None

        horas = int(total_segundos // 3600)
        minutos = int((total_segundos % 3600) // 60)

        resumen.append({
            'empleado': empleado,
            'ingreso': ingreso,
            'salida': salida,
            'horas': f'{horas:02d}:{minutos:02d}',
            'actividad': actividad or '-',
            'estado': 'EN CURSO' if ultimo_ingreso else 'FINALIZADO'
        })

    resumen.sort(key=lambda x: x['empleado'].apellido)

    return render_template(
        'reporte_diario.html',
        resumen=resumen,
        fecha=hoy
    )


# =========================
# REPORTE DIARIO POR BLOQUES
# =========================
@asistencias_bp.route('/reporte-diario-bloques')
@login_required
def reporte_diario_bloques():

    hoy = datetime.now().date()
    #empresa = get_empresa_activa()

    asistencias = (
        Asistencia.query
        .join(Empleado)
        .filter(
            db.func.date(Asistencia.fecha_hora) == hoy,
            Asistencia.empresa_id == current_user.empresa_id

        )
        .order_by(Empleado.apellido, Asistencia.fecha_hora)
        .all()
    )

    # Agrupar por empleado
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

        # Si quedó un ingreso sin salida
        if bloque_actual:
            bloques.append(bloque_actual)

    return render_template(
        'reporte_diario_bloques.html',
        bloques=bloques,
        fecha=hoy
    )


# =========================
# DETALLE DIARIO POR BLOQUES
# =========================
@asistencias_bp.route('/reporte-diario/<int:empleado_id>')
@login_required
def reporte_diario_bloques_detalle(empleado_id):

    hoy = datetime.now().date()
    #empresa = get_empresa_activa()

    empleado = Empleado.query.get_or_404(empleado_id)

    asistencias = (
        Asistencia.query
        .filter(
            Asistencia.empleado_id == empleado_id,
            Asistencia.empresa_id == current_user.empresa_id
,
            db.func.date(Asistencia.fecha_hora) == hoy
        )
        .order_by(Asistencia.fecha_hora)
        .all()
    )

    bloques = []
    bloque_actual = None

    for a in asistencias:

        if a.tipo == 'INGRESO':
            bloque_actual = {
                'ingreso': a.fecha_hora,
                'salida': None,
                'actividad': a.actividad,
                'estado': 'INCOMPLETO',
                'horas': '00:00'
            }

        elif a.tipo == 'SALIDA' and bloque_actual:
            salida = a.fecha_hora
            ingreso = bloque_actual['ingreso']

            total_segundos = (salida - ingreso).total_seconds()
            horas = int(total_segundos // 3600)
            minutos = int((total_segundos % 3600) // 60)

            bloque_actual.update({
                'salida': salida,
                'horas': f'{horas:02d}:{minutos:02d}',
                'estado': 'OK'
            })

            bloques.append(bloque_actual)
            bloque_actual = None

    if bloque_actual:
        bloques.append(bloque_actual)

    return render_template(
        'reporte_diario_detalle.html',
        empleado=empleado,
        bloques=bloques,
        fecha=hoy
    )



