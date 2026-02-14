from app.models import db, AuditLog
from flask_login import current_user
from app.security import obtener_ip_cliente


def registrar_evento(accion, descripcion=None, entidad="SISTEMA"):
    """
    Guarda un evento de auditoría del sistemaaaa
    """

    try:
        if not current_user.is_authenticated:
            return

        evento = AuditLog(
            empresa_id=current_user.empresa_id,
            usuario_id=current_user.id,
            accion=accion,
            entidad=entidad,   # 🔥 AHORA SI
            descripcion=descripcion,
            ip=obtener_ip_cliente()
        )

        db.session.add(evento)
        db.session.commit()

    except Exception as e:
        print("ERROR AUDITORIA:", e)
