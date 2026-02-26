from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from app import login_manager, current_user
from app.models import Usuario, Empresa, db, Sucursal
from app.audit import registrar_evento


auth_bp = Blueprint('auth', __name__)


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

#________________________________________________________________________________________________________________-
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():

    # 👉 si ya está logueado, evitar volver a loguear
    from flask_login import current_user
    if current_user.is_authenticated:
        if current_user.rol == "empleado":
            return redirect(url_for("fichaje.home"))
        else:
            return redirect(url_for("main.dashboard"))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email == current_app.config["SUPERADMIN_EMAIL"] and \
                password == current_app.config["SUPERADMIN_PASSWORD"]:
            session["superadmin"] = True
            return redirect(url_for("superadmin.panel"))

        user = Usuario.query.filter_by(email=email, activo=True).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('Credenciales inválidas', 'danger')
            return redirect(url_for('auth.login'))
        # 🚫 Bloquear si empresa está desactivada
        if user.empresa and not user.empresa.activa:
            flash("La empresa se encuentra desactivada. Contacte al administrador.", "danger")
            return redirect(url_for('auth.login'))

        login_user(user)

        registrar_evento(
            "LOGIN",
            f"Inicio de sesión: {user.email}",
            "USUARIO"
        )

        # ==========================================
        # 🔥 NUEVA LÓGICA DE REDIRECCIÓN
        # ==========================================

        # 1️⃣ Si viene parámetro next (ej QR)
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)

        # 2️⃣ Si no hay next → decidir por rol
        if user.rol == "empleado":
            return redirect(url_for("fichaje.home"))
        else:
            return redirect(url_for("main.dashboard"))

    return render_template('login.html')

#________________________________________________________________________________________________________________-
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


#________________________________________________________________________________________________________________-


# ==========================================
# REGISTRO EMPRESA + ADMIN
# ==========================================
@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():

    if request.method == 'POST':
        nombre_empresa = request.form.get('empresa')
        email = request.form.get('email')
        password = request.form.get('password')

        if not nombre_empresa or not email or not password:
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('auth.registro'))

        # 🚫 validar email único global
        existe = Usuario.query.filter_by(email=email).first()
        if existe:
            flash('Ese email ya está registrado', 'warning')
            return redirect(url_for('auth.registro'))

        # =========================
        # 1️⃣ Crear empresa
        # =========================
        empresa = Empresa(
            nombre=nombre_empresa,
            activa=True
        )
        db.session.add(empresa)
        db.session.flush()  # 🔥 obtenemos empresa.id sin commit
        # Crear sucursal principal automática
        sucursal = Sucursal(
            empresa_id=empresa.id,
            nombre="Sucursal Principal",
            activa=True
        )
        db.session.add(sucursal)
        db.session.flush()

        # =========================
        # 2️⃣ Crear usuario ADMIN
        # =========================
        admin = Usuario(
            empresa_id=empresa.id,
            email=email,
            password_hash=generate_password_hash(password),
            rol='admin',
            activo=True
        )
        db.session.add(admin)
        db.session.commit()

        flash('Empresa creada correctamente. Ya podés iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('registro.html')

#________________________________________________________________________________________________________________-

# ==========================================
# CAMBIAR MI CONTRASEÑA
# ==========================================
@auth_bp.route('/cambiar-password', methods=['GET','POST'])
@login_required
def cambiar_password():

    if request.method == 'POST':

        actual = request.form.get('actual')
        nueva = request.form.get('nueva')
        confirmar = request.form.get('confirmar')

        if not check_password_hash(current_user.password_hash, actual):
            flash("La contraseña actual es incorrecta", "danger")
            return redirect(url_for('auth.cambiar_password'))

        if nueva != confirmar:
            flash("Las contraseñas nuevas no coinciden", "warning")
            return redirect(url_for('auth.cambiar_password'))

        if len(nueva) < 6:
            flash("La contraseña debe tener al menos 6 caracteres", "warning")
            return redirect(url_for('auth.cambiar_password'))

        current_user.password_hash = generate_password_hash(nueva)
        db.session.commit()

        flash("Contraseña actualizada correctamente", "success")
        return redirect(url_for('main.dashboard'))

    return render_template("cambiar_password.html")