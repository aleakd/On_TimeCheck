from datetime import datetime
from zoneinfo import ZoneInfo

def evaluar_dia(empleado, fecha, horario, asistencias):

    tz_ar = ZoneInfo("America/Argentina/Buenos_Aires")

    ingreso = None
    salida = None

    # ordenar por hora
    asistencias = sorted(asistencias, key=lambda x: x.fecha_hora)

    for a in asistencias:
        if a.tipo == "INGRESO" and not ingreso:
            ingreso = a.fecha_hora.astimezone(tz_ar)

        elif a.tipo == "SALIDA":
            salida = a.fecha_hora.astimezone(tz_ar)

    # =========================
    # SIN PLANIFICACIÓN
    # =========================
    if not horario:
        return {
            "estado": "SIN_PLAN",
            "detalle": "-"
        }

    # =========================
    # FRANCO
    # =========================
    if horario.tipo == "FRANCO":

        if ingreso:
            return {
                "estado": "EXTRA",
                "detalle": "Día libre"
            }

        return {
            "estado": "FRANCO",
            "detalle": "-"
        }

    # =========================
    # TRABAJA
    # =========================
    if horario.tipo == "TRABAJA":

        if not ingreso:
            return {
                "estado": "AUSENTE",
                "detalle": "No fichó"
            }

        hora_turno = horario.hora_inicio

        if hora_turno:
            ingreso_dt = ingreso.replace(
                year=fecha.year,
                month=fecha.month,
                day=fecha.day
            )

            turno_dt = datetime.combine(
                fecha,
                hora_turno,
                tzinfo=tz_ar
            )

            if ingreso_dt > turno_dt:
                minutos_tarde = int((ingreso_dt - turno_dt).total_seconds() // 60)

                return {
                    "estado": "TARDE",
                    "detalle": f"{minutos_tarde} min tarde"
                }

        return {
            "estado": "OK",
            "detalle": "En horario"
        }

    # =========================
    # LICENCIA
    # =========================
    if horario.tipo == "LICENCIA":
        return {
            "estado": "LICENCIA",
            "detalle": "-"
        }

    return {
        "estado": "DESCONOCIDO",
        "detalle": "-"
    }