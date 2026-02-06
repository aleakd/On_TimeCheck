from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Empleado, db
from app.context import get_empresa_activa
from flask_login import login_required, current_user


empleados_bp = Blueprint('empleados', __name__, url_prefix='/empleados')


@empleados_bp.route('/')
def lista_empleados():
    empresa = get_empresa_activa()

    empleados = (
        Empleado.query
        .filter_by(empresa_id=current_user.empresa_id)
        .order_by(Empleado.apellido)
        .all()
    )
    return render_template('empleados.html', empleados=empleados)


@empleados_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_empleado():
    if request.method == 'POST':
        dni = request.form.get('dni', '').strip()
        apellido = request.form.get('apellido', '').strip()
        nombre = request.form.get('nombre', '').strip()

        if not dni or not apellido or not nombre:
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('empleados.nuevo_empleado'))

        #empresa = get_empresa_activa()

        existe = Empleado.query.filter_by(
            empresa_id=current_user.empresa_id,
            dni=dni
        ).first()
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

        flash('Empleado creado correctamente', 'success')
        return redirect(url_for('empleados.lista_empleados'))

    return render_template('empleado_form.html')


@empleados_bp.route('/toggle/<int:id>')
def toggle_empleado(id):
    empleado = Empleado.query.filter_by(
        id=id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    empleado.activo = not empleado.activo
    db.session.commit()

    estado = 'activado' if empleado.activo else 'desactivado'
    flash(f'Empleado {estado} correctamente', 'info')

    return redirect(url_for('empleados.lista_empleados'))
