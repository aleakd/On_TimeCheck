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

def ip_autorizada_empresa():
    """
    Verifica si la IP del cliente está permitida
    """
    empresa = current_user.empresa

    # Si la empresa no configuró seguridad → permitir
    if not empresa.ip_publica and not empresa.ip_rango:
        return True

    ip_cliente = obtener_ip_cliente()

    try:
        ip_cliente_obj = ipaddress.ip_address(ip_cliente)
    except:
        return False

    # ✔️ Validar IP fija
    if empresa.ip_publica:
        if ip_cliente == empresa.ip_publica:
            return True

    # ✔️ Validar rango CIDR
    if empresa.ip_rango:
        try:
            red = ipaddress.ip_network(empresa.ip_rango, strict=False)
            if ip_cliente_obj in red:
                return True
        except:
            pass

    return False


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
        if ip_cliente == sucursal.ip_publica:
            return True

    if sucursal.ip_rango:
        try:
            red = ipaddress.ip_network(sucursal.ip_rango, strict=False)
            if ip_cliente_obj in red:
                return True
        except:
            pass

    return False

def requiere_ip_empresa(func):
    @wraps(func)
    def wrapper(*args, **kwargs):

        if current_user.empleado:
            sucursal = current_user.empleado.sucursal

            if not sucursal.activa:
                flash("⛔ La sucursal está inactiva", "danger")
                return redirect(url_for('reportes.index'))

        if not ip_autorizada_sucursal():
            flash('⛔ No estás conectado a la red autorizada de la sucursal', 'danger')
            return redirect(url_for('reportes.index'))

        return func(*args, **kwargs)

    return wrapper