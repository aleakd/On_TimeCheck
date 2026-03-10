from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Empleado, db, Sucursal
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

    # Obtener sucursales de la empresa actual
    sucursales = Sucursal.query.filter_by(
        empresa_id=current_user.empresa_id,
        activa=True
    ).all()

    if request.method == 'POST':
        dni = request.form.get('dni', '').strip()
        apellido = request.form.get('apellido', '').strip()
        nombre = request.form.get('nombre', '').strip()
        turno_inicio = request.form.get('turno_inicio') or None
        turno_fin = request.form.get('turno_fin') or None
        tolerancia_minutos = request.form.get('tolerancia_minutos') or 15
        sucursal_id = request.form.get('sucursal_id')

        if not dni or not apellido or not nombre or not sucursal_id:
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('empleados.nuevo_empleado'))

        # Validar sucursal pertenece a la empresa
        sucursal = Sucursal.query.filter_by(
            id=sucursal_id,
            empresa_id=current_user.empresa_id
        ).first()

        if not sucursal:
            flash('Sucursal inválida', 'danger')
            return redirect(url_for('empleados.nuevo_empleado'))

        # Validar DNI dentro de la empresa
        existe = empleados_empresa().filter_by(dni=dni).first()
        if existe:
            flash('Ya existe un empleado con ese DNI', 'warning')
            return redirect(url_for('empleados.nuevo_empleado'))

        empleado = Empleado(
            empresa_id=current_user.empresa_id,
            sucursal_id=sucursal.id,
            dni=dni,
            apellido=apellido,
            nombre=nombre,
            activo=True,
            turno_inicio=turno_inicio,
            turno_fin=turno_fin,
            tolerancia_minutos=tolerancia_minutos
        )

        db.session.add(empleado)
        db.session.commit()

        registrar_evento(
            accion="CREAR",
            entidad="EMPLEADO",
            descripcion=f"Empleado creado: {apellido}, {nombre} - DNI {dni}"
        )

        flash('Empleado creado correctamente', 'success')
        return redirect(url_for('empleados.lista_empleados'))

    return render_template(
        'empleado_form.html',
        sucursales=sucursales
    )

# =========================
# EDITAR EMPLEADO
# =========================
@empleados_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_o_supervisor
def editar_empleado(id):

    empleado = empleados_empresa().filter_by(id=id).first_or_404()

    from app.models import Sucursal, Asistencia

    sucursales = Sucursal.query.filter_by(
        empresa_id=current_user.empresa_id,
        activa=True
    ).all()

    if request.method == 'POST':

        dni = request.form.get('dni')
        apellido = request.form.get('apellido')
        nombre = request.form.get('nombre')
        nueva_sucursal_id = int(request.form.get('sucursal_id'))

        # 🔒 Validar jornada abierta
        ultima = (
            Asistencia.query
            .filter_by(empleado_id=empleado.id)
            .order_by(Asistencia.fecha_hora.desc())
            .first()
        )

        if ultima and ultima.tipo == "INGRESO":
            flash("No se puede cambiar de sucursal con jornada abierta", "danger")
            return redirect(url_for('empleados.editar_empleado', id=id))

        # Guardar cambios
        empleado.dni = dni
        empleado.apellido = apellido
        empleado.nombre = nombre
        empleado.sucursal_id = nueva_sucursal_id

        db.session.commit()

        registrar_evento(
            "EDITAR",
            "EMPLEADO",
            f"Empleado editado: {apellido}, {nombre}"
        )

        flash("Empleado actualizado correctamente", "success")
        return redirect(url_for('empleados.lista_empleados'))

    return render_template(
        "empleado_form.html",
        empleado=empleado,
        sucursales=sucursales
    )

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
