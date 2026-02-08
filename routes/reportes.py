from flask import Blueprint, render_template, request
from app.models import Empleado, Asistencia
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy import extract
from flask_login import login_required, current_user


reportes_bp = Blueprint(
    'reportes',
    __name__,
    url_prefix='/reportes'
)

# =========================================================
# HOME REPORTES
# =========================================================
@reportes_bp.route('/')
@login_required
def index():
    return render_template('reportes_index.html')


# =========================================================
# REPORTE MENSUAL GENERAL (POR EMPRESA)
# =========================================================
@reportes_bp.route('/mensual')
@login_required
def reporte_mensual():

    hoy = datetime.now()

    # 🔒 Último mes cerrado por defecto
    primer_dia_mes_actual = hoy.replace(day=1)
    ultimo_dia_mes_anterior = primer_dia_mes_actual - timedelta(days=1)

    year = request.args.get('year', ultimo_dia_mes_anterior.year, type=int)
    month = request.args.get('month', ultimo_dia_mes_anterior.month, type=int)

    # 🔐 SOLO datos de la empresa del usuario logueado
    asistencias = (
        Asistencia.query
        .join(Empleado)
        .filter(
            Empleado.empresa_id == current_user.empresa_id,
            extract('year', Asistencia.fecha_hora) == year,
            extract('month', Asistencia.fecha_hora) == month
        )
        .order_by(Empleado.apellido, Asistencia.fecha_hora)
        .all()
    )

    # Agrupar por empleado
    registros_por_empleado = defaultdict(list)
    for a in asistencias:
        registros_por_empleado[a.empleado].append(a)

    resumen = []

    for empleado, registros in registros_por_empleado.items():

        ultimo_ingreso = None
        total_segundos = 0
        dias_trabajados = set()
        estado = 'CERRADO'

        for r in registros:
            if r.tipo == 'INGRESO':
                ultimo_ingreso = r.fecha_hora
                dias_trabajados.add(r.fecha_hora.date())

            elif r.tipo == 'SALIDA' and ultimo_ingreso:
                total_segundos += (r.fecha_hora - ultimo_ingreso).total_seconds()
                ultimo_ingreso = None

        if ultimo_ingreso:
            estado = 'INCOMPLETO'

        if total_segundos > 0:
            horas = int(total_segundos // 3600)
            minutos = int((total_segundos % 3600) // 60)

            resumen.append({
                'empleado': empleado,
                'horas': f'{horas:02d}:{minutos:02d}',
                'dias': len(dias_trabajados),
                'estado': estado
            })

    resumen.sort(key=lambda x: x['empleado'].apellido)

    nombre_mes = datetime(year, month, 1).strftime('%B %Y').capitalize()

    return render_template(
        'reporte_mensual.html',
        resumen=resumen,
        year=year,
        month=month,
        nombre_mes=nombre_mes
    )


# =========================================================
# DETALLE MENSUAL POR EMPLEADO (BLOQUES)
# =========================================================
@reportes_bp.route('/mensual/<int:empleado_id>')
@login_required
def detalle_mensual_empleado(empleado_id):

    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    if not year or not month:
        return "Mes inválido", 400

    # 🔐 empleado debe pertenecer a la empresa del usuario
    empleado = Empleado.query.filter_by(
        id=empleado_id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    asistencias = (
        Asistencia.query
        .filter(
            Asistencia.empleado_id == empleado_id,
            Asistencia.empresa_id == current_user.empresa_id,
            extract('year', Asistencia.fecha_hora) == year,
            extract('month', Asistencia.fecha_hora) == month
        )
        .order_by(Asistencia.fecha_hora)
        .all()
    )

    detalle = []
    bloque_actual = None
    contador_por_dia = defaultdict(int)

    for a in asistencias:

        if a.tipo == 'INGRESO':
            fecha = a.fecha_hora.date()
            contador_por_dia[fecha] += 1

            bloque_actual = {
                'fecha': fecha,
                'bloque': contador_por_dia[fecha],
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

            detalle.append(bloque_actual)
            bloque_actual = None

    if bloque_actual:
        detalle.append(bloque_actual)

    nombre_mes = datetime(year, month, 1).strftime('%B %Y').capitalize()

    return render_template(
        'reporte_mensual_detalle.html',
        empleado=empleado,
        detalle=detalle,
        nombre_mes=nombre_mes,
        year=year,
        month=month
    )
