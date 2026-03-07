from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app.models import db, Empleado, Asistencia
from app.multitenant import empleados_empresa, asistencias_empresa
from app.security import requiere_ip_empresa
from app.audit import registrar_evento

kiosco_bp = Blueprint(
    "kiosco",
    __name__,
    url_prefix="/kiosco"
)


# ==========================================
# PANTALLA KIOSCO
# ==========================================
@kiosco_bp.route("/")
@login_required
@requiere_ip_empresa
def pantalla():

    # solo admin o supervisor pueden usar kiosco
    if current_user.rol not in ["admin", "supervisor"]:
        return "No autorizado", 403

    return render_template("kiosco.html")


# ==========================================
# REGISTRAR FICHAJE POR DNI
# ==========================================
@kiosco_bp.route("/fichar", methods=["POST"])
@login_required
@requiere_ip_empresa
def fichar():

    dni = request.json.get("dni")

    empleado = (
        empleados_empresa()
        .filter_by(dni=dni, activo=True)
        .first()
    )

    if not empleado:
        return jsonify({
            "status": "error",
            "mensaje": "Empleado no encontrado"
        })

    ultima = (
        asistencias_empresa()
        .filter_by(empleado_id=empleado.id)
        .order_by(Asistencia.fecha_hora.desc())
        .first()
    )

    if not ultima or ultima.tipo == "SALIDA":
        tipo = "INGRESO"
    else:
        tipo = "SALIDA"

    asistencia = Asistencia(
        empleado_id=empleado.id,
        empresa_id=current_user.empresa_id,
        sucursal_id=empleado.sucursal_id,
        tipo=tipo,
        actividad="Kiosco"
    )

    db.session.add(asistencia)
    db.session.commit()

    registrar_evento(
        "CREAR",
        "ASISTENCIA",
        f"{tipo} kiosco - {empleado.apellido}, {empleado.nombre}"
    )

    return jsonify({
        "status": "ok",
        "tipo": tipo,
        "nombre": f"{empleado.apellido} {empleado.nombre}",
        "hora": datetime.now().strftime("%H:%M:%S"),
        "sucursal": empleado.sucursal.nombre
    })