from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from datetime import datetime, date
import calendar

from app.models import (
    HorarioEmpleado,
    HorarioBloque,
    Empleado,
    db
)
from app.multitenant import empleados_empresa



def migrar_horario_a_bloques(horario):

    """
    Compatibilidad temporal:
    convierte horarios viejos
    a bloques nuevos automáticamente.
    """

    # 🔥 ya tiene bloques
    if horario.bloques:
        return

    # 🔥 no tiene horarios viejos
    if not horario.hora_inicio or not horario.hora_fin:
        return

    bloque = HorarioBloque(
        horario_id=horario.id,
        hora_inicio=horario.hora_inicio,
        hora_fin=horario.hora_fin
    )

    db.session.add(bloque)

def validar_bloques(bloques):

    """
    Valida:
    - inicio < fin
    - sin superposición
    """

    bloques_ordenados = sorted(
        bloques,
        key=lambda b: b["inicio"]
    )

    for i, bloque in enumerate(bloques_ordenados):

        inicio = bloque["inicio"]
        fin = bloque["fin"]

        # 🔥 inicio debe ser menor
        if inicio >= fin:
            return False, (
                "La hora de inicio "
                "debe ser menor al fin"
            )

        # 🔥 comparar con siguiente
        if i < len(bloques_ordenados) - 1:

            siguiente = bloques_ordenados[i + 1]

            if fin > siguiente["inicio"]:
                return False, (
                    "Hay bloques superpuestos"
                )

    return True, None



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
    # ==========================================
    # 🔥 MIGRAR HORARIOS VIEJOS A BLOQUES
    # ==========================================

    for h in horarios:
        migrar_horario_a_bloques(h)

    db.session.commit()

    # ==========================================
    # INDEXAR
    # ==========================================

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
        anio=año,
        today=date.today()
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

    import json
    import calendar

    from datetime import (
        date,
        datetime
    )

    empleado_id = int(
        request.form.get("empleado_id")
    )

    anio = int(
        request.form.get("anio")
    )

    mes = int(
        request.form.get("mes")
    )

    dias_laborales = request.form.getlist(
        "dias"
    )

    # ==========================================
    # 🔥 LEER BLOQUES
    # ==========================================

    bloques_json = request.form.get(
        "bloques"
    )

    bloques = json.loads(
        bloques_json
    )

    bloques_parseados = []

    for b in bloques:

        inicio = datetime.strptime(
            b["inicio"],
            "%H:%M"
        ).time()

        fin = datetime.strptime(
            b["fin"],
            "%H:%M"
        ).time()

        bloques_parseados.append({
            "inicio": inicio,
            "fin": fin
        })

    # ==========================================
    # 🔥 VALIDAR BLOQUES
    # ==========================================

    valido, error = validar_bloques(
        bloques_parseados
    )

    if not valido:
        return error, 400

    # ==========================================
    # 🔥 RECORRER MES
    # ==========================================

    _, total_dias = calendar.monthrange(
        anio,
        mes
    )

    for d in range(1, total_dias + 1):

        fecha = date(anio, mes, d)

        if str(fecha.weekday()) in dias_laborales:
            tipo = "TRABAJA"
        else:
            tipo = "FRANCO"

        horario = HorarioEmpleado.query.filter_by(
            empleado_id=empleado_id,
            fecha=fecha
        ).first()

        if not horario:

            horario = HorarioEmpleado(
                empleado_id=empleado_id,
                fecha=fecha,
                tipo=tipo
            )

            db.session.add(horario)
            db.session.flush()

        horario.tipo = tipo

        # ==========================================
        # 🔥 LIMPIAR BLOQUES VIEJOS
        # ==========================================

        horario.bloques.clear()

        # ==========================================
        # 🔥 SI ES FRANCO
        # ==========================================

        if tipo != "TRABAJA":

            horario.hora_inicio = None
            horario.hora_fin = None

            continue

        # ==========================================
        # 🔥 CREAR BLOQUES
        # ==========================================

        for b in bloques_parseados:

            bloque = HorarioBloque(
                horario_id=horario.id,
                hora_inicio=b["inicio"],
                hora_fin=b["fin"]
            )

            db.session.add(bloque)

        # ==========================================
        # 🔥 COMPATIBILIDAD TEMPORAL
        # ==========================================

        primer = bloques_parseados[0]

        horario.hora_inicio = primer["inicio"]
        horario.hora_fin = primer["fin"]

    db.session.commit()

    return "OK"

@horarios_bp.route("/editar-dia", methods=["POST"])
@login_required
def editar_dia():

    import json
    from datetime import datetime

    empleado_id = int(
        request.form.get("empleado_id")
    )

    fecha = request.form.get("fecha")
    tipo = request.form.get("tipo")

    fecha_dt = datetime.strptime(
        fecha,
        "%Y-%m-%d"
    ).date()

    horario = HorarioEmpleado.query.filter_by(
        empleado_id=empleado_id,
        fecha=fecha_dt
    ).first()

    if not horario:
        horario = HorarioEmpleado(
            empleado_id=empleado_id,
            fecha=fecha_dt,
            tipo=tipo
        )

        db.session.add(horario)
        db.session.flush()

    horario.tipo = tipo

    # ==========================================
    # 🔥 LIMPIAR BLOQUES ANTERIORES
    # ==========================================

    horario.bloques.clear()

    # ==========================================
    # 🔥 FRANCO / LICENCIA
    # ==========================================

    if tipo != "TRABAJA":

        horario.hora_inicio = None
        horario.hora_fin = None

        db.session.commit()

        return "OK"

    # ==========================================
    # 🔥 LEER BLOQUES
    # ==========================================

    bloques_json = request.form.get("bloques")

    bloques = json.loads(bloques_json)

    bloques_parseados = []

    for b in bloques:

        inicio = datetime.strptime(
            b["inicio"],
            "%H:%M"
        ).time()

        fin = datetime.strptime(
            b["fin"],
            "%H:%M"
        ).time()

        bloques_parseados.append({
            "inicio": inicio,
            "fin": fin
        })

    # ==========================================
    # 🔥 VALIDAR
    # ==========================================

    valido, error = validar_bloques(
        bloques_parseados
    )

    if not valido:
        return error, 400

    # ==========================================
    # 🔥 CREAR BLOQUES
    # ==========================================

    for b in bloques_parseados:

        bloque = HorarioBloque(
            horario_id=horario.id,
            hora_inicio=b["inicio"],
            hora_fin=b["fin"]
        )

        db.session.add(bloque)

    # ==========================================
    # 🔥 COMPATIBILIDAD TEMPORAL
    # ==========================================

    primer = bloques_parseados[0]

    horario.hora_inicio = primer["inicio"]
    horario.hora_fin = primer["fin"]

    db.session.commit()

    return "OK"