from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db, Asistencia, AuditLog
from app.multitenant import asistencias_empresa
from app.audit import registrar_evento
from app.services.validacion_fichaje_service import (
    validar_acceso_fichaje
)
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone
from app.services.horarios_service import evaluar_llegada_tarde, obtener_turno_dia
from app.services.geolocalizacion_service import (ubicacion_permitida)


fichaje_bp = Blueprint(
    "fichaje",
    __name__,
    url_prefix="/fichaje"
)

# =====================================================
# HOME FICHAJE (pantalla de 2 botones)
# =====================================================
@fichaje_bp.route("/")
@login_required
def home():

    if current_user.rol not in ["empleado", "supervisor"]:
        return redirect(url_for("main.dashboard"))

    empleado_id = current_user.empleado_id

    ultima = (
        asistencias_empresa()
        .filter(Asistencia.empleado_id == empleado_id)
        .order_by(Asistencia.fecha_hora.desc())
        .first()
    )

    puede_ingresar = False
    puede_salir = False

    if not ultima:
        puede_ingresar = True
    elif ultima.tipo == "SALIDA":
        puede_ingresar = True
    elif ultima.tipo == "INGRESO":
        puede_salir = True

    return render_template(
        "fichaje_home.html",
        puede_ingresar=puede_ingresar,
        puede_salir=puede_salir,
        ultima=ultima
    )


# =====================================================
# ACCIÓN INGRESO (1 CLICK)
# =====================================================
@fichaje_bp.route("/ingreso", methods=["POST"])
@login_required

def fichar_ingreso():

    if current_user.rol not in ["empleado", "supervisor"]:
        return redirect(url_for("main.dashboard"))

    empleado_id = current_user.empleado_id


    ultima = (
        asistencias_empresa()
        .filter(Asistencia.empleado_id == empleado_id)
        .order_by(Asistencia.fecha_hora.desc())
        .first()
    )

    if ultima and ultima.tipo == "INGRESO":
        flash("Ya tenés un ingreso activo", "warning")
        return redirect(url_for("fichaje.home"))

    tz_ar = ZoneInfo("America/Argentina/Buenos_Aires")
    empleado = current_user.empleado
    sucursal = empleado.sucursal

    fecha_hora_ar = datetime.now(tz_ar)


    # =========================
    # ⏰ CONTROL DE LLEGADA TARDE
    # SOLO PRIMER INGRESO DEL DÍA
    # =========================

    inicio_dia_ar = fecha_hora_ar.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    fin_dia_ar = inicio_dia_ar + timedelta(days=1)

    inicio_dia = inicio_dia_ar.astimezone(
        timezone.utc
    )

    fin_dia = fin_dia_ar.astimezone(
        timezone.utc
    )

    ingreso_previo = (
        asistencias_empresa()
        .filter(
            Asistencia.empleado_id == empleado_id,
            Asistencia.tipo == "INGRESO",
            Asistencia.fecha_hora >= inicio_dia,
            Asistencia.fecha_hora < fin_dia
        )
        .first()
    )

    # 🔥 SOLO evaluar primer ingreso
    if not ingreso_previo:

        if evaluar_llegada_tarde(
                empleado,
                fecha_hora_ar
        ):

            ya_existe = db.session.query(
                db.exists().where(
                    db.and_(
                        AuditLog.empresa_id == current_user.empresa_id,
                        AuditLog.entidad == "PUNTUALIDAD",

                        # 🔥 EMPLEADO ESPECÍFICO
                        AuditLog.descripcion.contains(
                            f"{empleado.apellido}, {empleado.nombre}"
                        ),

                        AuditLog.created_at >= inicio_dia.astimezone(timezone.utc),

                        AuditLog.created_at < fin_dia.astimezone(timezone.utc)
                    )
                )
            ).scalar()

            if not ya_existe:
                turno = obtener_turno_dia(
                    empleado,
                    fecha_hora_ar
                )

                hora_turno_str = (
                    turno["inicio"].strftime('%H:%M')
                    if turno and turno["inicio"]
                    else "--:--"
                )

                registrar_evento(
                    accion="ALERTA",
                    entidad="PUNTUALIDAD",
                    descripcion=(
                        f"Llegada tarde: "
                        f"{empleado.apellido}, {empleado.nombre} "
                        f"(Ingreso {fecha_hora_ar.strftime('%H:%M')}, "
                        f"Turno {hora_turno_str})"
                    )
                )

    # ==========================================
    # VALIDAR GEOLOCALIZACIÓN
    # ==========================================

    latitud = request.form.get("latitud")
    longitud = request.form.get("longitud")

    latitud = (
        float(latitud)
        if latitud else None
    )

    longitud = (
        float(longitud)
        if longitud else None
    )

    precision = request.form.get(
        "precision_metros"
    )

    precision = (
        float(precision)
        if precision else None
    )

    # ==========================================
    # PRECISIÓN GPS
    # ==========================================

    if precision and precision > 200:
        flash(
            (
                "La precisión de tu ubicación "
                "es demasiado baja. "
                "Intentá nuevamente."
            ),
            "warning"
        )

        return redirect(
            url_for("fichaje.home")
        )

    # ==========================================
    # VALIDACIÓN CENTRAL
    # ==========================================

    resultado_validacion = validar_acceso_fichaje(

        sucursal=sucursal,

        latitud=latitud,
        longitud=longitud
    )

    if not resultado_validacion["ok"]:
        flash(
            resultado_validacion["mensaje"],
            "danger"
        )

        return redirect(
            url_for("fichaje.home")
        )

    # =========================
    # 💾 GUARDAR ASISTENCIA
    # =========================
    asistencia = Asistencia(
        empleado_id=empleado_id,
        empresa_id=current_user.empresa_id,
        sucursal_id=current_user.empleado.sucursal_id,
        tipo="INGRESO",
        actividad="FICHAJE_APP",
        latitud=request.form.get("latitud") or None,
        longitud=request.form.get("longitud") or None,
        precision_metros=request.form.get("precision_metros") or None
    )

    db.session.add(asistencia)
    db.session.commit()

    registrar_evento(
        "CREAR",
        "ASISTENCIA",
        f"INGRESO rápido - {current_user.email}"
    )

    flash("Ingreso registrado", "success")
    return redirect(url_for("fichaje.home"))


# =====================================================
# ACCIÓN SALIDA (1 CLICK)
# =====================================================
@fichaje_bp.route("/salida", methods=["POST"])
@login_required

def fichar_salida():

    if current_user.rol not in ["empleado", "supervisor"]:
        return redirect(url_for("main.dashboard"))

    empleado_id = current_user.empleado_id

    ultima = (
        asistencias_empresa()
        .filter(Asistencia.empleado_id == empleado_id)
        .order_by(Asistencia.fecha_hora.desc())
        .first()
    )

    if not ultima or ultima.tipo == "SALIDA":
        flash("No hay ingreso activo", "warning")
        return redirect(url_for("fichaje.home"))

    asistencia = Asistencia(
        empleado_id=empleado_id,
        empresa_id=current_user.empresa_id,
        sucursal_id=current_user.empleado.sucursal_id,
        tipo="SALIDA",
        actividad="FICHAJE_APP",
        latitud=request.form.get("latitud") or None,
        longitud=request.form.get("longitud") or None,
        precision_metros=request.form.get("precision_metros") or None
    )

    db.session.add(asistencia)
    db.session.commit()

    registrar_evento(
        "CREAR",
        "ASISTENCIA",
        f"SALIDA rápida - {current_user.email}"
    )

    flash("Salida registrada", "success")
    return redirect(url_for("fichaje.home"))