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
        # ==========================================
        # 🔥 MIGRACIÓN AUTOMÁTICA
        # ==========================================

        if (
                not horario.bloques
                and horario.hora_inicio
                and horario.hora_fin
        ):
            from app.models import (
                HorarioBloque,
                db
            )

            bloque = HorarioBloque(
                horario_id=horario.id,
                hora_inicio=horario.hora_inicio,
                hora_fin=horario.hora_fin
            )

            db.session.add(bloque)
            db.session.commit()

            db.session.refresh(horario)

        bloques = sorted(
            horario.bloques,
            key=lambda b: b.hora_inicio
        )

        inicio = None
        fin = None

        if bloques:
            inicio = bloques[0].hora_inicio
            fin = bloques[-1].hora_fin

        else:
            # compatibilidad vieja temporal
            inicio = horario.hora_inicio
            fin = horario.hora_fin

        return {
            "tipo": horario.tipo,
            "inicio": inicio,
            "fin": fin,
            "bloques": bloques
        }

    # fallback al turno fijo del empleado

    return None

def evaluar_llegada_tarde(
    empleado,
    fecha_hora
):

    tz = ZoneInfo(
        "America/Argentina/Buenos_Aires"
    )

    fecha_hora = fecha_hora.astimezone(tz)

    turno = obtener_turno_dia(
        empleado,
        fecha_hora
    )

    if not turno:
        return False

    if turno["tipo"] != "TRABAJA":
        return False

    bloques = turno.get("bloques", [])

    if not bloques:
        return False

    tolerancia = (
        empleado.tolerancia_minutos or 0
    )

    # ==========================================
    # 🔥 PRIMER BLOQUE DEL DÍA
    # ==========================================

    bloques_ordenados = sorted(
        bloques,
        key=lambda b: b.hora_inicio
    )

    primer_bloque = bloques_ordenados[0]

    turno_dt = datetime.combine(
        fecha_hora.date(),
        primer_bloque.hora_inicio,
        tzinfo=tz
    )

    limite = turno_dt + timedelta(
        minutes=tolerancia
    )

    return fecha_hora > limite