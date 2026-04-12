from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app.roles import solo_admin
from app.models import Usuario, Empleado, db
from app.audit import registrar_evento


usuarios_bp = Blueprint(
    'usuarios',
    __name__,
    url_prefix='/usuarios'
)

# =========================
# LISTA USUARIOS EMPRESA
# =========================
@usuarios_bp.route('/')
@login_required
@solo_admin
def lista_usuarios():

    usuarios = (
        Usuario.query
        .filter_by(empresa_id=current_user.empresa_id)
        .order_by(Usuario.email)
        .all()
    )

    return render_template('usuarios.html', usuarios=usuarios)


# =========================
# CREAR USUARIO
# =========================
@usuarios_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
@solo_admin
def nuevo_usuario():

    empleados = Empleado.query.filter_by(
        empresa_id=current_user.empresa_id,
        activo=True
    ).order_by(Empleado.apellido).all()

    # 🚨 UX IMPORTANTE: no se pueden crear usuarios empleados sin empleados
    if request.method == 'GET' and not empleados:
        flash('Primero debes crear empleados antes de crear usuarios de tipo empleado', 'warning')

    if request.method == 'POST':
        email = request.form.get('email').lower().strip()
        password = request.form.get('password')
        rol = request.form.get('rol')
        empleado_id = request.form.get('empleado_id')
        empleado_id = int(empleado_id) if empleado_id else None

        if empleado_id:
            existe_usuario = Usuario.query.filter_by(
                empleado_id=empleado_id,
                empresa_id=current_user.empresa_id
            ).first()

            if existe_usuario:
                flash('Este empleado ya tiene un usuario asignado', 'warning')
                return redirect(url_for('empleados.lista_empleados'))


        # No permitir crear usuario EMPLEADO sin empleado vinculado
        if rol != 'admin' and not empleado_id:
            flash('Debe seleccionar un empleado para este tipo de usuario', 'danger')
            return redirect(url_for('usuarios.nuevo_usuario'))
        # 🔐 seguridad multiempresa
        if empleado_id:
            empleado = Empleado.query.filter_by(
                id=empleado_id,
                empresa_id=current_user.empresa_id
            ).first()

            if not empleado:
                flash('Empleado inválido', 'danger')
                return redirect(url_for('usuarios.nuevo_usuario'))

        if not email or not password or not rol:
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('usuarios.nuevo_usuario'))

        existe = Usuario.query.filter_by(email=email).first()
        if existe:
            flash('Ya existe un usuario con ese email', 'warning')
            return redirect(url_for('usuarios.nuevo_usuario'))

        usuario = Usuario(
            empresa_id=current_user.empresa_id,
            email=email,
            password_hash=generate_password_hash(password),
            rol=rol,
            empleado_id=int(empleado_id) if empleado_id else None,
            activo=True
        )

        db.session.add(usuario)
        db.session.commit()

        # 📝 AUDITORIA SEGURIDAD
        registrar_evento(
            accion="CREAR",
            entidad="USUARIO",
            descripcion=f"Usuario creado: {email} | Rol: {rol}"
        )

        flash('Usuario creado correctamente', 'success')
        return redirect(url_for('usuarios.lista_usuarios'))

    return render_template('usuario_form.html', empleados=empleados)



# =========================
# ACTIVAR / DESACTIVAR USUARIO
# =========================
@usuarios_bp.route('/toggle/<int:id>')
@login_required
@solo_admin
def toggle_usuario(id):

    usuario = Usuario.query.filter_by(
        id=id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    usuario.activo = not usuario.activo
    db.session.commit()

    estado = 'activado' if usuario.activo else 'desactivado'

    # 📝 AUDITORIA SEGURIDAD
    registrar_evento(
        accion="EDITAR",
        entidad="USUARIO",
        descripcion=f"Usuario {estado}: {usuario.email}"
    )

    flash(f'Usuario {estado}', 'info')

    return redirect(url_for('usuarios.lista_usuarios'))

# =====================================
# EDITAR USUARIO (ROL + PASSWORD + EMPLEADO)
# =====================================
@usuarios_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@solo_admin
def editar_usuario(id):

    usuario = Usuario.query.filter_by(
        id=id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    # 🔹 empleados disponibles para vincular
    empleados = Empleado.query.filter_by(
        empresa_id=current_user.empresa_id,
        activo=True
    ).order_by(Empleado.apellido).all()

    if request.method == 'POST':

        rol = request.form.get('rol')
        password = request.form.get('password')
        empleado_id = request.form.get('empleado_id') or None

        # 🔐 Validación importante SaaS
        if rol != 'admin' and not empleado_id:
            flash("Debes seleccionar un empleado para este usuario", "danger")
            return redirect(url_for('usuarios.editar_usuario', id=id))

        # actualizar rol
        usuario.rol = rol

        # actualizar vínculo empleado
        if rol == 'empleado':
            usuario.empleado_id = empleado_id
        else:
            usuario.empleado_id = None

        # cambiar password SOLO si se escribió algo
        if password:
            usuario.password_hash = generate_password_hash(password)

        db.session.commit()

        # 📝 AUDITORIA SEGURIDAD
        registrar_evento(
            accion="EDITAR",
            entidad="USUARIO",
            descripcion=f"Usuario modificado: {usuario.email} | Nuevo rol: {usuario.rol}"
        )
        flash("Usuario actualizado correctamente", "success")
        return redirect(url_for('usuarios.lista_usuarios'))

    return render_template(
        "usuario_edit.html",
        usuario=usuario,
        empleados=empleados
    )


# ==========================================
# RESET PASSWORD (ADMIN)
# ==========================================
@usuarios_bp.route('/reset-password/<int:id>', methods=['POST'])
@login_required
@solo_admin
def reset_password(id):

    usuario = Usuario.query.filter_by(
        id=id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    nueva_password = request.form.get('nueva_password')

    if not nueva_password or len(nueva_password) < 6:
        flash("La contraseña debe tener al menos 6 caracteres", "warning")
        return redirect(url_for('usuarios.lista_usuarios'))

    usuario.password_hash = generate_password_hash(nueva_password)
    db.session.commit()

    flash("Contraseña reseteada correctamente", "success")
    return redirect(url_for('usuarios.lista_usuarios'))



@usuarios_bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
@solo_admin  # o el decorador que uses
def eliminar_usuario(id):

    usuario = Usuario.query.filter_by(
        id=id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    # 🚫 evitar que se elimine a sí mismo
    if usuario.id == current_user.id:
        flash("No podés eliminar tu propio usuario", "danger")
        return redirect(url_for('usuarios.lista_usuarios'))

    if usuario.rol == 'admin':
        flash("No se puede eliminar un administrador", "warning")
        return redirect(...)

    db.session.delete(usuario)
    db.session.commit()

    flash("Usuario eliminado correctamente", "success")
    return redirect(url_for('usuarios.lista_usuarios'))