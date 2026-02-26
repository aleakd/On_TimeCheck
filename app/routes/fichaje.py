from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from app.models import db, Asistencia
from app.multitenant import asistencias_empresa
from app.audit import registrar_evento
from app.security import requiere_ip_empresa

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

    # 🔒 solo empleados pueden usar fichaje
    if current_user.rol != "empleado":
        return redirect(url_for("main.dashboard"))

    empleado_id = current_user.empleado_id

    # buscar última asistencia del empleado
    ultima = (
        asistencias_empresa()
        .filter(Asistencia.empleado_id == empleado_id)
        .order_by(Asistencia.fecha_hora.desc())
        .first()
    )

    # decidir qué botón habilitar
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

    asistencia = Asistencia(
        empleado_id=empleado_id,
        empresa_id=current_user.empresa_id,
        sucursal_id=current_user.empleado.sucursal_id,
        tipo="INGRESO",
        actividad="Fichaje rápido"
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
        actividad="Fichaje rápido"
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
