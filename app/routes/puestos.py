from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_required,
    current_user
)

from app.models import (
    db,
    Puesto
)

from app.roles import (
    admin_o_supervisor
)

from app.audit import registrar_evento


puestos_bp = Blueprint(
    'puestos',
    __name__,
    url_prefix='/puestos'
)


# ==========================================
# LISTA
# ==========================================

@puestos_bp.route('/')
@login_required
@admin_o_supervisor
def lista_puestos():

    puestos = (
        Puesto.query
        .filter_by(
            empresa_id=current_user.empresa_id
        )
        .order_by(Puesto.nombre)
        .all()
    )

    return render_template(
        'puestos.html',
        puestos=puestos
    )


# ==========================================
# NUEVO
# ==========================================

@puestos_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
@admin_o_supervisor
def nuevo_puesto():

    if request.method == 'POST':

        nombre = (
            request.form.get('nombre') or ''
        ).strip()

        color = (
            request.form.get('color') or 'primary'
        ).strip()

        if not nombre:

            flash(
                'Debe ingresar un nombre',
                'danger'
            )

            return redirect(
                url_for('puestos.nuevo_puesto')
            )

        existe = Puesto.query.filter_by(
            empresa_id=current_user.empresa_id,
            nombre=nombre
        ).first()

        if existe:

            flash(
                'Ese puesto ya existe',
                'warning'
            )

            return redirect(
                url_for('puestos.nuevo_puesto')
            )

        puesto = Puesto(

            empresa_id=current_user.empresa_id,

            nombre=nombre,

            color=color,

            activo=True
        )

        db.session.add(puesto)
        db.session.commit()

        registrar_evento(
            accion="CREAR",
            entidad="PUESTO",
            descripcion=f"Puesto creado: {nombre}"
        )

        flash(
            'Puesto creado correctamente',
            'success'
        )

        return redirect(
            url_for('puestos.lista_puestos')
        )

    return render_template(
        'puesto_form.html'
    )


# ==========================================
# EDITAR
# ==========================================

@puestos_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_o_supervisor
def editar_puesto(id):

    puesto = Puesto.query.filter_by(
        id=id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    if request.method == 'POST':

        nombre = (
            request.form.get('nombre') or ''
        ).strip()

        color = (
            request.form.get('color') or 'primary'
        ).strip()

        if not nombre:

            flash(
                'Debe ingresar un nombre',
                'danger'
            )

            return redirect(
                url_for(
                    'puestos.editar_puesto',
                    id=id
                )
            )

        puesto.nombre = nombre
        puesto.color = color

        db.session.commit()

        registrar_evento(
            accion="EDITAR",
            entidad="PUESTO",
            descripcion=f"Puesto editado: {nombre}"
        )

        flash(
            'Puesto actualizado',
            'success'
        )

        return redirect(
            url_for('puestos.lista_puestos')
        )

    return render_template(
        'puesto_form.html',
        puesto=puesto
    )


# ==========================================
# ACTIVAR / DESACTIVAR
# ==========================================

@puestos_bp.route('/toggle/<int:id>')
@login_required
@admin_o_supervisor
def toggle_puesto(id):

    puesto = Puesto.query.filter_by(
        id=id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    puesto.activo = not puesto.activo

    db.session.commit()

    estado = (
        'activado'
        if puesto.activo
        else 'desactivado'
    )

    registrar_evento(
        accion="EDITAR",
        entidad="PUESTO",
        descripcion=f"Puesto {estado}: {puesto.nombre}"
    )

    flash(
        f'Puesto {estado}',
        'info'
    )

    return redirect(
        url_for('puestos.lista_puestos')
    )