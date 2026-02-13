from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Empleado, Asistencia
from datetime import datetime
from sqlalchemy import extract
from app.multitenant import empleados_empresa, asistencias_empresa

main_bp = Blueprint('main', __name__)


# ==========================================
# DASHBOARD PRINCIPAL
# ==========================================
@main_bp.route('/')
@login_required
def dashboard():

    hoy = datetime.now().date()
    ahora = datetime.now()

    # 👥 empleados activos
    total_empleados = empleados_empresa().filter_by(activo=True).count()

    # 🕒 asistencias hoy
    asistencias_hoy = (
        asistencias_empresa()
        .filter(extract('day', Asistencia.fecha_hora) == hoy.day)
        .count()
    )

    # 👷 empleados actualmente trabajando (INGRESO sin SALIDA)
    trabajando = 0

    empleados = empleados_empresa().all()

    for emp in empleados:
        ultima = (
            asistencias_empresa()
            .filter_by(empleado_id=emp.id)
            .order_by(Asistencia.fecha_hora.desc())
            .first()
        )

        if ultima and ultima.tipo == 'INGRESO':
            trabajando += 1

    # ⏱ horas acumuladas del mes
    year = ahora.year
    month = ahora.month

    asistencias_mes = (
        asistencias_empresa()
        .filter(
            extract('year', Asistencia.fecha_hora) == year,
            extract('month', Asistencia.fecha_hora) == month
        )
        .order_by(Asistencia.fecha_hora)
        .all()
    )

    total_segundos = 0
    ultimo_ingreso = {}

    for a in asistencias_mes:
        if a.tipo == 'INGRESO':
            ultimo_ingreso[a.empleado_id] = a.fecha_hora

        elif a.tipo == 'SALIDA' and a.empleado_id in ultimo_ingreso:
            delta = (a.fecha_hora - ultimo_ingreso[a.empleado_id]).total_seconds()
            total_segundos += delta
            ultimo_ingreso.pop(a.empleado_id)

    horas_mes = int(total_segundos // 3600)

    return render_template(
        'dashboard.html',
        total_empleados=total_empleados,
        asistencias_hoy=asistencias_hoy,
        trabajando=trabajando,
        horas_mes=horas_mes
    )
