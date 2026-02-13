from functools import wraps
from flask_login import current_user
from flask import abort


# ===============================
# SOLO ADMIN
# ===============================
def solo_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.rol != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# ===============================
# ADMIN O SUPERVISOR
# ===============================
def admin_o_supervisor(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.rol not in ['admin', 'supervisor']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
