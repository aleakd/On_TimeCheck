from app.security import (
    ip_autorizada_sucursal,
    sucursal_requiere_ip,
    sucursal_requiere_geo,
    obtener_ip_cliente
)
from flask_login import current_user

from app.services.geolocalizacion_service import (
    ubicacion_permitida
)


# =====================================================
# VALIDACIÓN CENTRAL FICHAJE
# =====================================================

def validar_acceso_fichaje(

    sucursal,

    latitud=None,
    longitud=None
):

    # ==========================================
    # ADMIN Y SUPERVISOR LIBRES
    # ==========================================

    if current_user.rol in [

        "admin",
        "supervisor"
    ]:

        return {
            "ok": True,
            "mensaje": None
        }

    # ==========================================
    # SUCURSAL INACTIVA
    # ==========================================

    if not sucursal.activa:

        return {
            "ok": False,
            "mensaje": "⛔ La sucursal está inactiva."
        }

    # ==========================================
    # VALIDACIÓN IP
    # ==========================================

    requiere_ip = sucursal_requiere_ip(
        sucursal
    )

    if requiere_ip:

        if not ip_autorizada_sucursal():

            return {
                "ok": False,
                "mensaje": (
                    "⛔ Debés conectarte "
                    "desde la red autorizada."
                )
            }

    # ==========================================
    # VALIDACIÓN GEO
    # ==========================================

    requiere_geo = sucursal_requiere_geo(
        sucursal
    )

    if requiere_geo:

        geo_ok = ubicacion_permitida(

            sucursal,

            latitud,
            longitud
        )

        if not geo_ok:

            return {
                "ok": False,
                "mensaje": (
                    "📍 Te encontrás fuera "
                    "del área permitida."
                )
            }

    # ==========================================
    # ACCESO OK
    # ==========================================

    return {
        "ok": True,
        "mensaje": None
    }