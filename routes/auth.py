from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from app import login_manager
from app.models import Usuario, Empresa, db

auth_bp = Blueprint('auth', __name__)





@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

#________________________________________________________________________________________________________________-
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = Usuario.query.filter_by(email=email, activo=True).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('Credenciales inválidas', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user)
        return redirect(url_for('reportes.index'))

    return render_template('login.html')
#________________________________________________________________________________________________________________-
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))



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
