from flask import Blueprint, render_template, request, send_file
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from flask_login import login_required, current_user
from app.services.excel_export import (
    exportar_reporte_mensual_excel,
    exportar_detalle_empleado_excel
)
from app.roles import admin_o_supervisor
from app.models import Empleado, Asistencia, db, Sucursal, HorarioEmpleado
from app.multitenant import empleados_empresa, asistencias_empresa
from zoneinfo import ZoneInfo
from app.utils.evaluacion import evaluar_dia


MESES_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

reportes_bp = Blueprint('reportes', __name__, url_prefix='/reportes')

@reportes_bp.route('/')
@login_required
@admin_o_supervisor
def index():

    return render_template("reportes_index.html")
# =========================================================
# 🧠 HELPERS (CLAVE PARA TODO)
# =========================================================
def obtener_rango_mes(year, month, tz_ar):
    inicio_mes_ar = datetime(year, month, 1, tzinfo=tz_ar)

    if month == 12:
        fin_mes_ar = datetime(year + 1, 1, 1, tzinfo=tz_ar)
    else:
        fin_mes_ar = datetime(year, month + 1, 1, tzinfo=tz_ar)

    inicio_utc = inicio_mes_ar.astimezone(timezone.utc)
    fin_utc = fin_mes_ar.astimezone(timezone.utc)

    return inicio_utc, fin_utc


def obtener_asistencias_mes(empleado_id, inicio_utc, fin_utc):
    buffer_inicio = inicio_utc - timedelta(hours=12)
    buffer_fin = fin_utc + timedelta(hours=12)

    return (
        asistencias_empresa()
        .filter(
            Asistencia.fecha_hora >= buffer_inicio,
            Asistencia.fecha_hora < buffer_fin,
            *( [Asistencia.empleado_id == empleado_id] if empleado_id else [] )
        )
        .order_by(Asistencia.fecha_hora)
        .all()
    )


def procesar_bloques(registros, tz_ar, month):

    bloques = []
    ingreso = None

    for r in registros:

        fecha_local = r.fecha_hora.astimezone(tz_ar)

        if r.tipo == "INGRESO":
            ingreso = fecha_local

        elif r.tipo == "SALIDA" and ingreso:

            bloques.append({
                "fecha": ingreso.date(),
                "ingreso": ingreso,
                "salida": fecha_local,
                "actividad": r.actividad or "-"
            })

            ingreso = None

    # ingreso sin salida (real)
    if ingreso:
        bloques.append({
            "fecha": ingreso.date(),
            "ingreso": ingreso,
            "salida": None,
            "actividad": "-"
        })

    # 🔥 FILTRAR BIEN POR MES
    bloques_mes = []

    for b in bloques:

        mes_ingreso = b["ingreso"].month
        mes_salida = b["salida"].month if b["salida"] else None

        # ✔ incluir si el bloque pertenece al mes
        if mes_ingreso == month or mes_salida == month:
            bloques_mes.append(b)

    # 🔥 calcular resultado final
    resultado = []

    for b in bloques_mes:

        if b["salida"]:
            segundos = (b["salida"] - b["ingreso"]).total_seconds()
            h = int(segundos // 3600)
            m = int((segundos % 3600) // 60)

            estado = "OK"
            horas = f"{h:02d}:{m:02d}"

        else:
            estado = "INCOMPLETO"
            horas = "00:00"

        resultado.append({
            "fecha": b["fecha"],
            "ingreso": b["ingreso"],
            "salida": b["salida"],
            "horas": horas,
            "estado": estado,
            "actividad": b["actividad"]
        })

    return resultado




# =========================================================
# REPORTE MENSUAL
# =========================================================
@reportes_bp.route('/mensual')
@login_required
@admin_o_supervisor
def reporte_mensual():

    tz_ar = ZoneInfo("America/Argentina/Buenos_Aires")

    hoy = datetime.now(tz_ar)
    year = request.args.get('year', hoy.year, type=int)
    month = request.args.get('month', hoy.month, type=int)

    sucursal_id = request.args.get('sucursal_id', type=int)

    sucursales = Sucursal.query.filter_by(
        empresa_id=current_user.empresa_id
    ).all()

    inicio_utc, fin_utc = obtener_rango_mes(year, month, tz_ar)

    asistencias = obtener_asistencias_mes(None, inicio_utc, fin_utc)

    registros_por_empleado = defaultdict(list)

    for a in asistencias:
        registros_por_empleado[a.empleado].append(a)

    resumen = []

    for empleado, registros in registros_por_empleado.items():

        bloques = procesar_bloques(registros, tz_ar, month)

        total_segundos = sum(
            (b["salida"] - b["ingreso"]).total_seconds()
            for b in bloques if b["salida"]
        )

        if total_segundos > 0:
            horas = int(total_segundos // 3600)
            minutos = int((total_segundos % 3600) // 60)

            estado = "OK"

            if any(b["estado"] == "INCOMPLETO" for b in bloques):
                estado = "INCOMPLETO"

            resumen.append({
                "empleado": empleado,
                "empleado_id": empleado.id,
                "horas": f"{horas:02d}:{minutos:02d}",
                "dias": len(set(b["fecha"] for b in bloques)),
                "estado": estado
            })

    resumen.sort(key=lambda x: x["empleado"].apellido)

    return render_template(
        "reporte_mensual.html",
        resumen=resumen,
        year=year,
        month=month,
        nombre_mes=f"{MESES_ES[month]} {year}",
        sucursales=sucursales,
        sucursal_id=sucursal_id
    )


# =========================================================
# DETALLE MENSUAL EMPLEADO
# =========================================================
@reportes_bp.route('/mensual/<int:empleado_id>')
@login_required
@admin_o_supervisor
def detalle_mensual_empleado(empleado_id):

    tz_ar = ZoneInfo("America/Argentina/Buenos_Aires")

    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    empleado = empleados_empresa().filter_by(id=empleado_id).first_or_404()

    inicio_utc, fin_utc = obtener_rango_mes(year, month, tz_ar)

    registros = obtener_asistencias_mes(empleado_id, inicio_utc, fin_utc)

    detalle = procesar_bloques(registros, tz_ar, month)

    return render_template(
        "reporte_mensual_detalle.html",
        empleado=empleado,
        detalle=detalle,
        nombre_mes=f"{MESES_ES[month]} {year}",
        year=year,
        month=month
    )


# =========================================================
# EXPORTAR MENSUAL EXCEL
# =========================================================
@reportes_bp.route('/mensual/excel')
@login_required
@admin_o_supervisor
def exportar_mensual_excel():

    tz_ar = ZoneInfo("America/Argentina/Buenos_Aires")

    hoy = datetime.now(tz_ar)
    year = request.args.get('year', hoy.year, type=int)
    month = request.args.get('month', hoy.month, type=int)

    inicio_utc, fin_utc = obtener_rango_mes(year, month, tz_ar)

    asistencias = obtener_asistencias_mes(None, inicio_utc, fin_utc)

    registros_por_empleado = defaultdict(list)

    for a in asistencias:
        registros_por_empleado[a.empleado].append(a)

    resumen = []

    for empleado, registros in registros_por_empleado.items():

        bloques = procesar_bloques(registros, tz_ar, month)

        total_segundos = sum(
            (b["salida"] - b["ingreso"]).total_seconds()
            for b in bloques if b["salida"]
        )

        if total_segundos > 0:
            horas = int(total_segundos // 3600)
            minutos = int((total_segundos % 3600) // 60)

            estado = "OK"

            if any(b["estado"] == "INCOMPLETO" for b in bloques):
                estado = "INCOMPLETO"

            resumen.append({
                "empleado": empleado,
                "empleado_id": empleado.id,
                "horas": f"{horas:02d}:{minutos:02d}",
                "dias": len(set(b["fecha"] for b in bloques)),
                "estado": estado
            })

    file = exportar_reporte_mensual_excel(
        current_user.empresa.nombre,
        f"{MESES_ES[month]} {year}",
        resumen
    )

    return send_file(file, as_attachment=True)


@reportes_bp.route('/mensual/<int:empleado_id>/excel')
@login_required
@admin_o_supervisor
def exportar_detalle_empleado_excel_route(empleado_id):

    tz_ar = ZoneInfo("America/Argentina/Buenos_Aires")

    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    empleado = empleados_empresa().filter_by(id=empleado_id).first_or_404()

    inicio_utc, fin_utc = obtener_rango_mes(year, month, tz_ar)

    registros = obtener_asistencias_mes(empleado_id, inicio_utc, fin_utc)

    detalle = procesar_bloques(registros, tz_ar, month)

    file = exportar_detalle_empleado_excel(
        empleado,
        f"{MESES_ES[month]} {year}",
        detalle
    )

    return send_file(file, as_attachment=True)


# =========================================================
# REPORTE DIARIO (FIX TOTAL)
# =========================================================
@reportes_bp.route('/diario')
@login_required
@admin_o_supervisor
def reporte_diario():

    tz_ar = ZoneInfo("America/Argentina/Buenos_Aires")

    fecha = request.args.get("fecha")
    hoy = datetime.strptime(fecha, "%Y-%m-%d").date() if fecha else datetime.now(tz_ar).date()

    sucursal_id = request.args.get("sucursal_id", type=int)

    inicio_ar = datetime.combine(hoy, datetime.min.time(), tzinfo=tz_ar)
    fin_ar = inicio_ar + timedelta(days=1)

    inicio_utc = inicio_ar.astimezone(timezone.utc)
    fin_utc = fin_ar.astimezone(timezone.utc)

    buffer_inicio = inicio_utc - timedelta(hours=12)
    buffer_fin = fin_utc + timedelta(hours=12)

    query = asistencias_empresa().filter(
        Asistencia.fecha_hora >= buffer_inicio,
        Asistencia.fecha_hora < buffer_fin
    )

    if sucursal_id:
        query = query.filter(Asistencia.sucursal_id == sucursal_id)

    asistencias = query.order_by(Asistencia.fecha_hora).all()

    registros_por_empleado = defaultdict(list)

    for a in asistencias:
        fecha_local = a.fecha_hora.astimezone(tz_ar).date()

        if fecha_local != hoy:
            continue

        # 🔥 asegurar sucursal correcta (doble validación)
        if sucursal_id and a.sucursal_id != sucursal_id:
            continue

        registros_por_empleado[a.empleado].append(a)

    resumen = []

    for empleado, registros in registros_por_empleado.items():

        bloques = []
        ingreso = None

        for r in registros:
            fecha_local = r.fecha_hora.astimezone(tz_ar)

            if r.tipo == "INGRESO":
                ingreso = fecha_local

            elif r.tipo == "SALIDA" and ingreso:
                bloques.append((ingreso, fecha_local))
                ingreso = None

        total_segundos = sum(
            (salida - ingreso).total_seconds()
            for ingreso, salida in bloques
        )

        horas = "00:00"
        estado = "AUSENTE"

        if total_segundos > 0:
            h = int(total_segundos // 3600)
            m = int((total_segundos % 3600) // 60)
            horas = f"{h:02d}:{m:02d}"
            estado = "OK"

        elif ingreso:
            estado = "INCOMPLETO"

        resumen.append({
            "empleado": empleado,
            "ingreso": bloques[0][0] if bloques else ingreso,
            "salida": bloques[-1][1] if bloques else None,
            "horas": horas,
            "estado": estado,
            "detalle": f"{len(bloques)} bloque(s)"
        })

    sucursales = Sucursal.query.filter_by(
        empresa_id=current_user.empresa_id
    ).all()

    return render_template(
        "reporte_diario.html",
        resumen=resumen,
        fecha=hoy,
        sucursales=sucursales,
        sucursal_id=sucursal_id
    )
# =========================================================
# REPORTE DIARIO por empleado
# =========================================================
@reportes_bp.route('/diario/<int:empleado_id>')
@login_required
@admin_o_supervisor
def reporte_diario_detalle(empleado_id):

    tz_ar = ZoneInfo("America/Argentina/Buenos_Aires")

    fecha = request.args.get("fecha")

    if not fecha:
        return "Fecha requerida", 400

    dia = datetime.strptime(fecha, "%Y-%m-%d").date()

    inicio_ar = datetime.combine(dia, datetime.min.time(), tzinfo=tz_ar)
    fin_ar = inicio_ar + timedelta(days=1)

    inicio_utc = inicio_ar.astimezone(timezone.utc)
    fin_utc = fin_ar.astimezone(timezone.utc)

    buffer_inicio = inicio_utc - timedelta(hours=12)
    buffer_fin = fin_utc + timedelta(hours=12)

    registros = (
        asistencias_empresa()
        .filter(
            Asistencia.empleado_id == empleado_id,
            Asistencia.fecha_hora >= buffer_inicio,
            Asistencia.fecha_hora < buffer_fin
        )
        .order_by(Asistencia.fecha_hora)
        .all()
    )

    bloques = []
    ingreso = None

    for r in registros:

        fecha_local = r.fecha_hora.astimezone(tz_ar)

        if fecha_local.date() != dia:
            continue

        if r.tipo == "INGRESO":
            ingreso = fecha_local

        elif r.tipo == "SALIDA" and ingreso:
            segundos = (fecha_local - ingreso).total_seconds()
            h = int(segundos // 3600)
            m = int((segundos % 3600) // 60)

            bloques.append({
                "ingreso": ingreso,
                "salida": fecha_local,
                "horas": f"{h:02d}:{m:02d}",
                "estado": "OK",
                "actividad": r.actividad or "-"
            })
            ingreso = None

    # ingreso sin salida
    if ingreso:
        bloques.append({
            "ingreso": ingreso,
            "salida": None,
            "horas": "00:00",
            "estado": "INCOMPLETO",
            "actividad": "-"
        })

    empleado = Empleado.query.get_or_404(empleado_id)

    return render_template(
        "reporte_diario_detalle.html",
        empleado=empleado,
        bloques=bloques,  # 👈 clave
        fecha=dia
    )

