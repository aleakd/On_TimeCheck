from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.models import db, Empleado, Asistencia, AuditLog
from app.multitenant import empleados_empresa, asistencias_empresa
from app.security import requiere_ip_empresa
from app.audit import registrar_evento
from app.services.horarios_service import evaluar_llegada_tarde, obtener_turno_dia


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

    tz_ar = ZoneInfo("America/Argentina/Buenos_Aires")

    # =========================
    # ⏰ CONTROL LLEGADA TARDE
    # =========================
    if tipo == "INGRESO":

        fecha_hora_ar = datetime.now(tz_ar)

        if evaluar_llegada_tarde(empleado, fecha_hora_ar):

            inicio_dia = fecha_hora_ar.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            fin_dia = inicio_dia + timedelta(days=1)

            ya_existe = db.session.query(db.exists().where(
                db.and_(
                    AuditLog.empresa_id == current_user.empresa_id,
                    AuditLog.entidad == "PUNTUALIDAD",
                    AuditLog.created_at >= inicio_dia.astimezone(timezone.utc),
                    AuditLog.created_at < fin_dia.astimezone(timezone.utc)
                )
            )).scalar()

            if not ya_existe:

                turno = obtener_turno_dia(empleado, fecha_hora_ar)

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

    # =========================
    # 💾 GUARDAR ASISTENCIA
    # =========================
    asistencia = Asistencia(
        empleado_id=empleado.id,
        empresa_id=current_user.empresa_id,
        sucursal_id=empleado.sucursal_id,
        tipo=tipo,
        actividad="KIOSCO",
        fecha_hora=datetime.now(timezone.utc)
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
        "hora": datetime.now(tz_ar).strftime("%H:%M:%S"),
        "sucursal": empleado.sucursal.nombre
    })