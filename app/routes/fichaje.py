from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, Asistencia, AuditLog
from app.multitenant import asistencias_empresa
from app.audit import registrar_evento
from app.security import requiere_ip_empresa
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone


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

    if current_user.rol != "empleado":
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
@fichaje_bp.route("/ingreso")
@login_required
@requiere_ip_empresa
def fichar_ingreso():

    if current_user.rol != "empleado":
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

    # =========================
    # ⏰ CONTROL DE LLEGADA TARDE
    # =========================
    fecha_hora_ar = datetime.now(tz_ar)

    if empleado.turno_inicio:

        hora_turno = empleado.turno_inicio
        tolerancia = empleado.tolerancia_minutos or 0

        inicio_turno_dt = datetime.combine(
            fecha_hora_ar.date(),
            hora_turno,
            tzinfo=tz_ar
        )

        limite_dt = inicio_turno_dt + timedelta(minutes=tolerancia)

        if fecha_hora_ar > limite_dt:

            # 🔍 evitar duplicados en el mismo día
            inicio_dia = fecha_hora_ar.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            fin_dia = inicio_dia + timedelta(days=1)

            ya_existe = db.session.query(db.exists().where(
                db.and_(
                    AuditLog.empresa_id == current_user.empresa_id,
                    AuditLog.entidad == "PUNTUALIDAD",
                    AuditLog.descripcion.like(f"%{empleado.apellido}%"),
                    AuditLog.created_at >= inicio_dia.astimezone(timezone.utc),
                    AuditLog.created_at < fin_dia.astimezone(timezone.utc)
                )
            )).scalar()

            if not ya_existe:
                registrar_evento(
                    accion="ALERTA",
                    entidad="PUNTUALIDAD",
                    descripcion=(
                        f"Llegada tarde: "
                        f"{empleado.apellido}, {empleado.nombre} "
                        f"(Ingreso {fecha_hora_ar.strftime('%H:%M')}, "
                        f"Turno {hora_turno.strftime('%H:%M')})"
                    )
                )

    # =========================
    # 💾 GUARDAR ASISTENCIA (UTC)
    # =========================
    asistencia = Asistencia(
        empleado_id=empleado_id,
        empresa_id=current_user.empresa_id,
        sucursal_id=current_user.empleado.sucursal_id,
        tipo="INGRESO",
        actividad="FICHAJE_APP"
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
@fichaje_bp.route("/salida")
@requiere_ip_empresa
@login_required
def fichar_salida():

    if current_user.rol != "empleado":
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
        actividad="FICHAJE_APP"
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