from flask_login import current_user
from app.models import Empleado, Asistencia, Empresa


# ================================
# EMPRESA ACTIVA DEL USUARIO
# ================================
def empresa_actual():
    return current_user.empresa


# ================================
# QUERY SEGURAS (AISLADAS)
# ================================
def empleados_empresa():
    return Empleado.query.filter_by(
        empresa_id=current_user.empresa_id
    )


def asistencias_empresa():
    return Asistencia.query.filter_by(
        empresa_id=current_user.empresa_id
    )


def empresa_por_id(empresa_id):
    return Empresa.query.filter_by(
        id=empresa_id,
        activa=True
    ).first()
