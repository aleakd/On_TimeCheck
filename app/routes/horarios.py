from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from datetime import datetime, date
import calendar

from app.models import HorarioEmpleado, Empleado, db
from app.multitenant import empleados_empresa

horarios_bp = Blueprint(
    "horarios",
    __name__,
    url_prefix="/horarios"
)


@horarios_bp.route("/")
@login_required
def calendario():

    año = request.args.get("anio", type=int) or datetime.now().year
    mes = request.args.get("mes", type=int) or datetime.now().month

    empleados = empleados_empresa().filter_by(activo=True).all()

    # días del mes
    _, total_dias = calendar.monthrange(año, mes)

    dias = [date(año, mes, d) for d in range(1, total_dias + 1)]

    # traer horarios existentes
    horarios = HorarioEmpleado.query.filter(
        HorarioEmpleado.fecha >= dias[0],
        HorarioEmpleado.fecha <= dias[-1],
        HorarioEmpleado.empleado_id.in_([e.id for e in empleados])
    ).all()

    # indexar
    horarios_dict = {
        (h.empleado_id, h.fecha): h
        for h in horarios
    }

    return render_template(
        "horarios_calendario.html",
        empleados=empleados,
        dias=dias,
        horarios=horarios_dict,
        mes=mes,
        anio=año
    )

@horarios_bp.route("/guardar", methods=["POST"])
@login_required
def guardar():

    empleado_id = int(request.form.get("empleado_id"))
    fecha = datetime.strptime(request.form.get("fecha"), "%Y-%m-%d").date()

    tipo = request.form.get("tipo")
    hora_inicio = request.form.get("hora_inicio") or None
    hora_fin = request.form.get("hora_fin") or None

    existente = HorarioEmpleado.query.filter_by(
        empleado_id=empleado_id,
        fecha=fecha
    ).first()

    if not existente:
        existente = HorarioEmpleado(
            empleado_id=empleado_id,
            fecha=fecha
        )

    existente.tipo = tipo

    if hora_inicio:
        existente.hora_inicio = datetime.strptime(hora_inicio, "%H:%M").time()

    if hora_fin:
        existente.hora_fin = datetime.strptime(hora_fin, "%H:%M").time()

    db.session.add(existente)
    db.session.commit()

    return "OK"

@horarios_bp.route("/aplicar", methods=["POST"])
@login_required
def aplicar_horario():

    empleado_id = int(request.form.get("empleado_id"))
    anio = int(request.form.get("anio"))
    mes = int(request.form.get("mes"))

    hora_inicio = request.form.get("hora_inicio")
    hora_fin = request.form.get("hora_fin")

    dias_laborales = request.form.getlist("dias")
    # ej: ["0","1","2","3","4"] → lunes a viernes

    import calendar
    from datetime import date, datetime

    _, total_dias = calendar.monthrange(anio, mes)

    for d in range(1, total_dias + 1):

        fecha = date(anio, mes, d)

        if str(fecha.weekday()) in dias_laborales:
            tipo = "TRABAJA"
        else:
            tipo = "FRANCO"

        existente = HorarioEmpleado.query.filter_by(
            empleado_id=empleado_id,
            fecha=fecha
        ).first()

        if not existente:
            existente = HorarioEmpleado(
                empleado_id=empleado_id,
                fecha=fecha
            )

        existente.tipo = tipo

        if tipo == "TRABAJA":
            existente.hora_inicio = datetime.strptime(hora_inicio, "%H:%M").time()
            existente.hora_fin = datetime.strptime(hora_fin, "%H:%M").time()
        else:
            existente.hora_inicio = None
            existente.hora_fin = None

        db.session.add(existente)

    db.session.commit()

    return "OK"

@horarios_bp.route("/editar-dia", methods=["POST"])
@login_required
def editar_dia():

    from datetime import datetime

    empleado_id = int(request.form.get("empleado_id"))
    fecha = request.form.get("fecha")
    tipo = request.form.get("tipo")
    inicio = request.form.get("inicio")
    fin = request.form.get("fin")

    fecha_dt = datetime.strptime(fecha, "%Y-%m-%d").date()

    horario = HorarioEmpleado.query.filter_by(
        empleado_id=empleado_id,
        fecha=fecha_dt
    ).first()

    if not horario:
        horario = HorarioEmpleado(
            empleado_id=empleado_id,
            fecha=fecha_dt
        )

    horario.tipo = tipo

    if tipo == "TRABAJA" and inicio and fin:
        horario.hora_inicio = datetime.strptime(inicio, "%H:%M").time()
        horario.hora_fin = datetime.strptime(fin, "%H:%M").time()
    else:
        horario.hora_inicio = None
        horario.hora_fin = None

    db.session.add(horario)
    db.session.commit()

    return "OK"