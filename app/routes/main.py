from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Empleado, Asistencia, AuditLog, db
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from zoneinfo import ZoneInfo
from app.multitenant import empleados_empresa, asistencias_empresa
from collections import defaultdict
from app.services.horarios_service import obtener_turno_dia

main_bp = Blueprint('main', __name__)


# ==========================================
# DASHBOARD PRINCIPAL
# ==========================================
@main_bp.route('/')
@login_required
def dashboard():

    tz_ar = ZoneInfo("America/Argentina/Buenos_Aires")

    hoy = datetime.now(tz_ar).date()
    ahora = datetime.now()

    # 👥 empleados activos
    total_empleados = empleados_empresa().filter_by(activo=True).count()

    # 🕒 asistencias hoy
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

    # ⏱ horas del mes
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
    # ⛔ EMPLEADOS PENDIENTES DE INGRESO
    # ==========================================

    pendientes = []

    ahora_ar = datetime.now(tz_ar)

    for emp in empleados:

        turno = obtener_turno_dia(emp, ahora_ar)

        # no trabaja hoy → ignorar
        if not turno or turno["tipo"] != "TRABAJA":
            continue

        # sin horario → ignorar
        if not turno["inicio"]:
            continue

        # hora de inicio del turno
        turno_dt = datetime.combine(
            ahora_ar.date(),
            turno["inicio"],
            tzinfo=tz_ar
        )

        tolerancia = emp.tolerancia_minutos or 0
        limite = turno_dt + timedelta(minutes=tolerancia)

        # todavía no debería haber llegado → ignorar
        if ahora_ar <= limite:
            continue

        # buscar si ya fichó hoy
        inicio_dia = ahora_ar.replace(hour=0, minute=0, second=0, microsecond=0)
        fin_dia = inicio_dia + timedelta(days=1)

        ingreso = (
            asistencias_empresa()
            .filter(
                Asistencia.empleado_id == emp.id,
                Asistencia.tipo == "INGRESO",
                Asistencia.fecha_hora >= inicio_dia,
                Asistencia.fecha_hora < fin_dia
            )
            .first()
        )

        # si ya ingresó → no es pendiente
        if ingreso:
            continue

        pendientes.append({
            "nombre": f"{emp.apellido} {emp.nombre}",
            "hora": turno["inicio"].strftime("%H:%M")
        })

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

    labels = []
    data = []

    for dia in sorted(horas_por_dia.keys()):

        labels.append(dia.strftime("%d/%m"))
        data.append(round(horas_por_dia[dia] / 3600, 2))

    # ==========================================
    # 👤 EMPLEADOS SEGÚN ROL
    # ==========================================

    if current_user.rol == "empleado":

        empleados = [current_user.empleado]

    else:

        empleados = Empleado.query.filter_by(
            empresa_id=current_user.empresa_id,
            activo=True
        ).all()

    # ==========================================
    # ESTADO ACTUAL DEL PERSONAL
    # ==========================================

    subquery = (
        db.session.query(
            Asistencia.empleado_id,
            func.max(Asistencia.fecha_hora).label("ultima_fecha")
        )
        .filter(
            Asistencia.empresa_id == current_user.empresa_id
        )
        .group_by(Asistencia.empleado_id)
        .subquery()
    )

    ultimos_registros = (
        db.session.query(Asistencia)
        .join(
            subquery,
            (Asistencia.empleado_id == subquery.c.empleado_id) &
            (Asistencia.fecha_hora == subquery.c.ultima_fecha)
        )
        .all()
    )

    registro_dict = {r.empleado_id: r for r in ultimos_registros}

    empleados_estado = []

    for emp in empleados:

        registro = registro_dict.get(emp.id)

        if registro:

            estado = "ingreso" if registro.tipo == "INGRESO" else "salida"

            hora_ar = registro.fecha_hora.astimezone(tz_ar)

            empleados_estado.append({
                "nombre": f"{emp.apellido} {emp.nombre}",
                "estado": estado,
                "hora": hora_ar.strftime("%H:%M")
            })

        else:

            empleados_estado.append({
                "nombre": f"{emp.apellido} {emp.nombre}",
                "estado": "sin_registro",
                "hora": None
            })

    orden_prioridad = {
        "ingreso": 0,
        "sin_registro": 1,
        "salida": 2
    }

    empleados_estado.sort(key=lambda x: orden_prioridad[x["estado"]])

    # ==========================================
    # 👷 LISTA DE QUIENES ESTÁN TRABAJANDO
    # ==========================================

    empleados_trabajando = [
        emp for emp in empleados_estado
        if emp["estado"] == "ingreso"
    ]

    # ==========================================
    # ⚠ LLEGADAS TARDE HOY
    # ==========================================

    inicio_dia_ar = datetime.now(tz_ar).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    fin_dia_ar = inicio_dia_ar + timedelta(days=1)

    inicio_utc = inicio_dia_ar.astimezone(timezone.utc)
    fin_utc = fin_dia_ar.astimezone(timezone.utc)

    alertas_tarde = (
        db.session.query(AuditLog)
        .filter(
            AuditLog.empresa_id == current_user.empresa_id,
            AuditLog.entidad == "PUNTUALIDAD",
            AuditLog.created_at >= inicio_utc,
            AuditLog.created_at < fin_utc
        )
        .order_by(AuditLog.created_at.desc())
        .all()
    )

    # ==========================================
    # 📍 EMPLEADOS POR SUCURSAL (KIOSCO)
    # ==========================================

    from app.models import Sucursal

    # Traer sucursales
    sucursales = Sucursal.query.filter_by(
        empresa_id=current_user.empresa_id,
        activa=True
    ).all()

    # Inicializar estructura
    sucursales_data = {s.id: {
        "nombre": s.nombre,
        "empleados": []
    } for s in sucursales}

    # Usamos los últimos registros (ya calculados arriba)
    for emp in empleados:

        registro = registro_dict.get(emp.id)

        if not registro or not registro.sucursal_id:
            continue

        estado = "ACTIVO" if registro.tipo == "INGRESO" else "FUERA"

        hora_ar = registro.fecha_hora.astimezone(tz_ar)

        sucursal_id = registro.sucursal_id

        if sucursal_id in sucursales_data:
            sucursales_data[sucursal_id]["empleados"].append({
                "nombre": f"{emp.apellido} {emp.nombre}",
                "estado": estado,
                "hora": hora_ar.strftime("%H:%M")
            })

    return render_template(
        'dashboard.html',
        total_empleados=total_empleados,
        asistencias_hoy=asistencias_hoy,
        trabajando=trabajando,
        horas_mes=horas_mes,
        chart_labels=labels,
        chart_data=data,
        fecha_hoy=hoy,
        empleados_estado=empleados_estado,
        empleados_trabajando=empleados_trabajando,
        alertas_tarde=alertas_tarde,
        pendientes=pendientes,
        sucursales_data=sucursales_data
    )