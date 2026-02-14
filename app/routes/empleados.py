from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Empleado, db
from app.multitenant import empleados_empresa
from app.roles import solo_admin, admin_o_supervisor
from app.audit import registrar_evento


empleados_bp = Blueprint('empleados', __name__, url_prefix='/empleados')


# =========================
# LISTA EMPLEADOS
# =========================
@empleados_bp.route('/')
@login_required
@admin_o_supervisor
def lista_empleados():
    empleados = empleados_empresa().order_by(Empleado.apellido).all()
    return render_template('empleados.html', empleados=empleados)


# =========================
# NUEVO EMPLEADO
# =========================
@empleados_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
@admin_o_supervisor
def nuevo_empleado():

    if request.method == 'POST':
        dni = request.form.get('dni', '').strip()
        apellido = request.form.get('apellido', '').strip()
        nombre = request.form.get('nombre', '').strip()

        if not dni or not apellido or not nombre:
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('empleados.nuevo_empleado'))

        # 🔒 validar DNI dentro de la empresa del usuario
        existe = empleados_empresa().filter_by(dni=dni).first()
        if existe:
            flash('Ya existe un empleado con ese DNI', 'warning')
            return redirect(url_for('empleados.nuevo_empleado'))

        empleado = Empleado(
            empresa_id=current_user.empresa_id,
            dni=dni,
            apellido=apellido,
            nombre=nombre,
            activo=True
        )

        db.session.add(empleado)
        db.session.commit()

        # 📝 AUDITORIA
        registrar_evento(
            accion="CREAR",
            entidad="EMPLEADO",
            descripcion=f"Empleado creado: {apellido}, {nombre} - DNI {dni}"
        )

        flash('Empleado creado correctamente', 'success')
        return redirect(url_for('empleados.lista_empleados'))

    return render_template('empleado_form.html')


# =========================
# ACTIVAR / DESACTIVAR
# =========================
@empleados_bp.route('/toggle/<int:id>')
@login_required
@admin_o_supervisor
def toggle_empleado(id):

    # 🔒 seguridad SaaS real
    empleado = empleados_empresa().filter_by(id=id).first_or_404()

    empleado.activo = not empleado.activo
    db.session.commit()

    estado = 'activado' if empleado.activo else 'desactivado'

    # 📝 AUDITORIA
    registrar_evento(
        accion="EDITAR",
        entidad="EMPLEADO",
        descripcion=f"Empleado {estado}: {empleado.apellido}, {empleado.nombre} (ID {empleado.id})"
    )
    flash(f'Empleado {estado} correctamente', 'info')

    return redirect(url_for('empleados.lista_empleados'))
