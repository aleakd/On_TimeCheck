from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Empleado, Asistencia, db
from datetime import datetime
from sqlalchemy import extract
from app.multitenant import empleados_empresa, asistencias_empresa
from collections import defaultdict

main_bp = Blueprint('main', __name__)

from sqlalchemy import text

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

    # 🕒 asistencias hoy (fecha completa correcta)
    asistencias_hoy = (
        asistencias_empresa()
        .filter(db.func.date(Asistencia.fecha_hora) == hoy)
        .count()
    )

    # 👷 empleados trabajando ahora
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

    # ⏱ horas del mes en formato HH:MM
    primer_dia_mes = ahora.replace(day=1)

    asistencias_mes = (
        asistencias_empresa()
        .filter(Asistencia.fecha_hora >= primer_dia_mes)
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

    horas = int(total_segundos // 3600)
    minutos = int((total_segundos % 3600) // 60)
    horas_mes = f"{horas:02d}:{minutos:02d}"

    # ==========================================
    # 📈 HORAS POR DÍA (GRÁFICO)
    # ==========================================


    horas_por_dia = defaultdict(int)
    ultimo_ingreso = {}

    for a in asistencias_mes:
        fecha = a.fecha_hora.date()

        if a.tipo == 'INGRESO':
            ultimo_ingreso[a.empleado_id] = a.fecha_hora

        elif a.tipo == 'SALIDA' and a.empleado_id in ultimo_ingreso:
            delta = (a.fecha_hora - ultimo_ingreso[a.empleado_id]).total_seconds()
            horas_por_dia[fecha] += delta
            ultimo_ingreso.pop(a.empleado_id)

    # convertir a formato gráfico
    labels = []
    data = []

    for dia in sorted(horas_por_dia.keys()):
        labels.append(dia.strftime("%d/%m"))
        data.append(round(horas_por_dia[dia] / 3600, 2))



    return render_template(
        'dashboard.html',
        total_empleados=total_empleados,
        asistencias_hoy=asistencias_hoy,
        trabajando=trabajando,
        horas_mes=horas_mes,
        chart_labels=labels,
        chart_data=data
    )



@main_bp.route('/fix-db-default')
def fix_db_default():

    db.session.execute(text("""
        ALTER TABLE asistencia
        ALTER COLUMN fecha_hora SET DEFAULT NOW();
    """))

    db.session.execute(text("""
        ALTER TABLE audit_log
        ALTER COLUMN created_at SET DEFAULT NOW();
    """))

    db.session.execute(text("""
        ALTER TABLE usuario
        ALTER COLUMN created_at SET DEFAULT NOW();
    """))

    db.session.execute(text("""
        ALTER TABLE empresa
        ALTER COLUMN created_at SET DEFAULT NOW();
    """))

    db.session.commit()

    return "DEFAULT NOW() aplicado ✅"
