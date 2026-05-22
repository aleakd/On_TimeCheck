from flask import request
import ipaddress
from flask_login import current_user
from functools import wraps
from flask import flash, redirect, url_for

def obtener_ip_cliente():
    """
    Obtiene la IP real incluso detrás de proxies
    """
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()

    return request.remote_addr

def ip_autorizada_sucursal():

    # Si no tiene empleado asociado → permitir (admin, etc)
    if not current_user.empleado:
        return True

    empleado = current_user.empleado

    if not empleado.sucursal:
        return True

    sucursal = empleado.sucursal

    # 🔴 NUEVA REGLA
    if not sucursal.activa:
        return False

    # Si no configuró seguridad → permitir
    if not sucursal.ip_publica and not sucursal.ip_rango:
        return True

    ip_cliente = obtener_ip_cliente()

    try:
        ip_cliente_obj = ipaddress.ip_address(ip_cliente)
    except:
        return False

    if sucursal.ip_publica:

        ips_permitidas = [

            ip.strip()

            for ip in sucursal.ip_publica.split(',')

            if ip.strip()
        ]

        if ip_cliente in ips_permitidas:
            return True

    if sucursal.ip_rango:
        try:
            red = ipaddress.ip_network(sucursal.ip_rango, strict=False)
            if ip_cliente_obj in red:
                return True
        except:
            pass

    return False
def sucursal_requiere_ip(sucursal):

    # ==========================================
    # LIMPIAR IPs
    # ==========================================

    ip_publica = (
        sucursal.ip_publica or ""
    )

    ip_publica = ip_publica.strip()

    # eliminar comas vacías
    ips = [

        ip.strip()

        for ip in ip_publica.split(",")

        if ip.strip()
    ]

    # ==========================================
    # LIMPIAR CIDR
    # ==========================================

    ip_rango = (
        sucursal.ip_rango or ""
    ).strip()

    # ==========================================
    # VALIDACIÓN FINAL
    # ==========================================

    return bool(
        ips
        or
        ip_rango
    )
def sucursal_requiere_geo(sucursal):

    return bool(
        sucursal.geo_activa
        and
        sucursal.latitud is not None
        and
        sucursal.longitud is not None
    )
def requiere_validacion_fichaje(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        from app.services.validacion_fichaje_service import (
            validar_acceso_fichaje
        )

        if current_user.empleado:

            sucursal = current_user.empleado.sucursal

            resultado = validar_acceso_fichaje(
                sucursal=sucursal
            )

            if not resultado["ok"]:
                flash(
                    resultado["mensaje"],
                    "danger"
                )

                return redirect(
                    url_for("fichaje.home")
                )
        return func(*args, **kwargs)

    return wrapper