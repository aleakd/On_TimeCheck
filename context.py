from flask_login import current_user

def get_empresa_activa():
    if not current_user.is_authenticated:
        return None
    return current_user.empresa
