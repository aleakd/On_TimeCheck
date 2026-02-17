from flask import Blueprint, render_template, request
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy import extract
from flask_login import login_required
from app.roles import solo_admin, admin_o_supervisor
from app.models import Empleado, Asistencia, db
from app.multitenant import empleados_empresa, asistencias_empresa


MESES_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

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
@admin_o_supervisor
def reporte_mensual():

    hoy = datetime.utcnow()


    primer_dia_mes_actual = hoy.replace(day=1)
    ultimo_dia_mes_anterior = primer_dia_mes_actual - timedelta(days=1)

    year = request.args.get('year', ultimo_dia_mes_anterior.year, type=int)
    month = request.args.get('month', ultimo_dia_mes_anterior.month, type=int)

    # 🔒 QUERY MULTITENANT SEGURA
    asistencias = (
        asistencias_empresa()
        .join(Empleado)
        .filter(
            extract('year', Asistencia.fecha_hora) == year,
            extract('month', Asistencia.fecha_hora) == month
        )
        .order_by(Empleado.apellido, Asistencia.fecha_hora)
        .all()
    )

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
                'empleado_id': empleado.id,
                'horas': f'{horas:02d}:{minutos:02d}',
                'dias': len(dias_trabajados),
                'estado': estado
            })

    resumen.sort(key=lambda x: x['empleado'].apellido)

    nombre_mes = f"{MESES_ES[month]} {year}"


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

    # 🔒 EMPLEADO SEGURO POR EMPRESA
    empleado = empleados_empresa().filter_by(id=empleado_id).first_or_404()

    asistencias = (
        asistencias_empresa()
        .filter(
            Asistencia.empleado_id == empleado_id,
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

    nombre_mes = f"{MESES_ES[month]} {year}"


    return render_template(
        'reporte_mensual_detalle.html',
        empleado=empleado,
        detalle=detalle,
        nombre_mes=nombre_mes,
        year=year,
        month=month
    )


# =========================================================
# REPORTE DIARIO GENERAL
# =========================================================
@reportes_bp.route('/diario')
@login_required
@admin_o_supervisor
def reporte_diario():

    hoy = datetime.utcnow().date()


    asistencias = (
        asistencias_empresa()
        .join(Empleado)
        .filter(db.func.date(
    db.func.timezone(
        'America/Argentina/Buenos_Aires',
        Asistencia.fecha_hora
    )
) == hoy)
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
                    actividad = r.actividad

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
            'estado': 'OK' if not ultimo_ingreso else 'EN CURSO'
        })

    resumen.sort(key=lambda x: x['empleado'].apellido)

    return render_template(
        'reporte_diario.html',
        resumen=resumen,
        fecha=hoy
    )


# =========================================================
# REPORTE DIARIO POR BLOQUES (TODOS) este borrar
# =========================================================
@reportes_bp.route('/diario/bloques')
@login_required
@admin_o_supervisor
def reporte_diario_bloques():

    hoy = datetime.utcnow().date()


    asistencias = (
        asistencias_empresa()
        .join(Empleado)
        .filter(db.func.date(
    db.func.timezone(
        'America/Argentina/Buenos_Aires',
        Asistencia.fecha_hora
    )
) == hoy)
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


# =========================================================
# DETALLE DIARIO POR EMPLEADO
# =========================================================
@reportes_bp.route('/diario/<int:empleado_id>')
@login_required
@admin_o_supervisor
def reporte_diario_detalle(empleado_id):

    hoy = datetime.now().date()

    empleado = empleados_empresa().filter_by(id=empleado_id).first_or_404()

    asistencias = (
        asistencias_empresa()
        .filter(
            Asistencia.empleado_id == empleado_id,
            db.func.date(
                db.func.timezone(
                    'America/Argentina/Buenos_Aires',
                    Asistencia.fecha_hora
                )
            ) == hoy
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
            total_segundos = (a.fecha_hora - bloque_actual['ingreso']).total_seconds()
            horas = int(total_segundos // 3600)
            minutos = int((total_segundos % 3600) // 60)

            bloque_actual.update({
                'salida': a.fecha_hora,
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
