from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, Empleado, Asistencia, AuditLog
from app.multitenant import empleados_empresa, asistencias_empresa
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone
from app.security import requiere_ip_empresa
from app.audit import registrar_evento
from app.services.horarios_service import evaluar_llegada_tarde, obtener_turno_dia


asistencias_bp = Blueprint(
    'asistencias',
    __name__,
    url_prefix='/asistencias'
)


@asistencias_bp.route('/', methods=['GET', 'POST'])
@login_required
@requiere_ip_empresa
def marcar_asistencia():

    modo_empleado = current_user.rol == 'empleado'

    if modo_empleado:
        empleados = [current_user.empleado]
    else:
        empleados = (
            empleados_empresa()
            .filter_by(activo=True)
            .order_by(Empleado.apellido)
            .all()
        )

    tz_ar = ZoneInfo("America/Argentina/Buenos_Aires")
    ahora_ar = datetime.now(tz_ar)

    inicio_dia_ar = ahora_ar.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    fin_dia_ar = inicio_dia_ar + timedelta(days=1)

    inicio_utc = inicio_dia_ar.astimezone(timezone.utc)
    fin_utc = fin_dia_ar.astimezone(timezone.utc)

    asistencias_hoy = (
        asistencias_empresa()
        .join(Empleado)
        .filter(
            Asistencia.fecha_hora >= inicio_utc,
            Asistencia.fecha_hora < fin_utc
        )
        .order_by(Asistencia.fecha_hora.desc())
        .all()
    )

    if request.method == 'POST':

        if modo_empleado:
            empleado_id = int(current_user.empleado_id)
        else:
            empleado_id = int(request.form.get('empleado_id'))

        tipo = request.form.get('tipo')
        actividad = request.form.get('actividad')

        fecha_manual = request.form.get("fecha_manual")
        hora_manual = request.form.get("hora_manual")

        # =========================
        # 📅 FECHA (manual o automática)
        # =========================
        if current_user.rol == "admin" and fecha_manual and hora_manual:
            try:
                fecha_str = f"{fecha_manual} {hora_manual}"
                fecha_local = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
                fecha_local = fecha_local.replace(tzinfo=tz_ar)
                fecha_hora = fecha_local.astimezone(timezone.utc)
            except Exception:
                flash("❌ Fecha u hora manual inválida", "danger")
                return redirect(url_for('asistencias.marcar_asistencia'))
        else:
            fecha_hora = datetime.now(timezone.utc)

        # 🚫 evitar futuro
        if fecha_hora > datetime.now(timezone.utc):
            flash("❌ No se puede cargar asistencia en el futuro", "danger")
            return redirect(url_for('asistencias.marcar_asistencia'))

        # 🚫 validaciones básicas
        if not empleado_id or tipo not in ['INGRESO', 'SALIDA']:
            flash('❌ Datos inválidos', 'danger')
            return redirect(url_for('asistencias.marcar_asistencia'))

        if tipo == 'INGRESO' and not actividad:
            flash('⚠️ Debe seleccionar una actividad para el INGRESO', 'warning')
            return redirect(url_for('asistencias.marcar_asistencia'))

        # =========================
        # 🔁 CONTROL DE SECUENCIA
        # =========================
        ultima = (
            asistencias_empresa()
            .filter(
                Asistencia.empleado_id == empleado_id,
                Asistencia.fecha_hora < fecha_hora
            )
            .order_by(Asistencia.fecha_hora.desc())
            .first()
        )

        if ultima:
            if ultima.tipo == 'INGRESO' and tipo == 'INGRESO':
                flash('❌ Ya existe un INGRESO activo en ese momento', 'warning')
                return redirect(url_for('asistencias.marcar_asistencia'))

            if ultima.tipo == 'SALIDA' and tipo == 'SALIDA':
                flash('❌ No puede haber dos SALIDAS consecutivas', 'warning')
                return redirect(url_for('asistencias.marcar_asistencia'))
        else:
            if tipo == 'SALIDA':
                flash('❌ No puede registrar SALIDA sin INGRESO previo', 'warning')
                return redirect(url_for('asistencias.marcar_asistencia'))

        empleado = Empleado.query.get(empleado_id)

        # =========================
        # ⏰ CONTROL DE LLEGADA TARDE
        # =========================
        if tipo == "INGRESO":

            fecha_hora_ar = fecha_hora.astimezone(tz_ar)

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
            empleado_id=empleado_id,
            empresa_id=current_user.empresa_id,
            sucursal_id=empleado.sucursal_id,
            tipo=tipo,
            actividad=actividad if tipo == 'INGRESO' else None,
            fecha_hora=fecha_hora
        )

        db.session.add(asistencia)
        db.session.commit()

        registrar_evento(
            accion="CREAR",
            entidad="ASISTENCIA",
            descripcion=f"{tipo} | {empleado.apellido}, {empleado.nombre}"
        )

        flash('✅ Asistencia registrada correctamente', 'success')
        return redirect(url_for('asistencias.marcar_asistencia'))

    return render_template(
        'asistencias.html',
        empleados=empleados,
        asistencias_hoy=asistencias_hoy,
    )