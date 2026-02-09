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


def requiere_ip_empresa(func):
    @wraps(func)
    def wrapper(*args, **kwargs):

        if not ip_autorizada_empresa():
            flash('⛔ No estás conectado a la red autorizada de la empresa', 'danger')
            return redirect(url_for('reportes.index'))

        return func(*args, **kwargs)

    return wrapper