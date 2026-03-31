from datetime import datetime, timedelta
from app.models import HorarioEmpleado
from zoneinfo import ZoneInfo



def obtener_turno_dia(empleado, fecha):
    tz = ZoneInfo("America/Argentina/Buenos_Aires")

    fecha_local = fecha.astimezone(tz).date()

    horario = HorarioEmpleado.query.filter_by(
        empleado_id=empleado.id,
        fecha=fecha_local
    ).first()

    if horario:
        return {
            "tipo": horario.tipo,
            "inicio": horario.hora_inicio,
            "fin": horario.hora_fin
        }

    # fallback al turno fijo del empleado
    if empleado.turno_inicio:
        return {
            "tipo": "TRABAJA",
            "inicio": empleado.turno_inicio,
            "fin": empleado.turno_fin
        }

    return None

def evaluar_llegada_tarde(empleado, fecha_hora):

    tz = ZoneInfo("America/Argentina/Buenos_Aires")

    fecha_hora = fecha_hora.astimezone(tz)

    turno = obtener_turno_dia(empleado, fecha_hora)

    if not turno or turno["tipo"] != "TRABAJA":
        return False

    if not turno["inicio"]:
        return False

    tolerancia = empleado.tolerancia_minutos or 0

    # 🔥 misma lógica que reporte diario
    ingreso_dt = fecha_hora.replace(
        year=fecha_hora.year,
        month=fecha_hora.month,
        day=fecha_hora.day
    )

    turno_dt = datetime.combine(
        fecha_hora.date(),
        turno["inicio"],
        tzinfo=tz
    )

    limite = turno_dt + timedelta(minutes=tolerancia)

    return ingreso_dt > limite