from datetime import datetime
import pytz

ARG_TZ = pytz.timezone("America/Argentina/Buenos_Aires")

def ahora_argentina():
    """Devuelve datetime actual en zona Argentina"""
    return datetime.now(ARG_TZ)

def convertir_a_argentina(dt):
    """Convierte cualquier datetime a hora Argentina"""
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(ARG_TZ)
