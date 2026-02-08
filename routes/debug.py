from flask import Blueprint
from app.context import get_empresa_activa

debug_bp = Blueprint('debug', __name__, url_prefix='/debug')


@debug_bp.route('/empresa')
def debug_empresa():
    empresa = get_empresa_activa()

    if not empresa:
        return '❌ No hay empresa activa'

    return f'✅ Empresa activa: ID={empresa.id} | Nombre={empresa.nombre}'
