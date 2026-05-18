from math import radians
from math import sin
from math import cos
from math import sqrt
from math import atan2


# =====================================================
# DISTANCIA ENTRE DOS COORDENADAS
# =====================================================
def calcular_distancia_metros(
    lat1,
    lon1,
    lat2,
    lon2
):

    radio_tierra = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        +
        cos(radians(lat1))
        *
        cos(radians(lat2))
        *
        sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return radio_tierra * c


# =====================================================
# VALIDAR UBICACIÓN
# =====================================================
def ubicacion_permitida(
    sucursal,
    lat_empleado,
    lon_empleado
):
    # GEO desactivada
    if not sucursal.geo_activa:
        return True
    # sucursal sin coordenadas
    if (
        sucursal.latitud is None
        or
        sucursal.longitud is None
    ):
        return True

    # empleado sin coordenadas
    if (
        lat_empleado is None
        or
        lon_empleado is None
    ):
        return False

    distancia = calcular_distancia_metros(
        sucursal.latitud,
        sucursal.longitud,
        lat_empleado,
        lon_empleado
    )

    return distancia <= sucursal.radio_metros