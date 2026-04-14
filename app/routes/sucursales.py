from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, Sucursal
from app.roles import solo_admin
from app.audit import registrar_evento
import secrets
from app.models import Kiosco


sucursales_bp = Blueprint(
    'sucursales',
    __name__,
    url_prefix='/sucursales'
)

# =========================
# LISTA
# =========================
@sucursales_bp.route('/')
@login_required
@solo_admin
def lista_sucursales():

    sucursales = Sucursal.query.filter_by(
        empresa_id=current_user.empresa_id
    ).all()
    kioscos = Kiosco.query.filter_by(
        empresa_id=current_user.empresa_id,
        activo=True
    ).all()

    kioscos_por_sucursal = {
        k.sucursal_id: k for k in kioscos
    }

    return render_template(
        'sucursales.html',
        sucursales=sucursales,
        kioscos_por_sucursal=kioscos_por_sucursal
    )

# =========================
# NUEVA SUCURSAL
# =========================
@sucursales_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
@solo_admin
def nueva_sucursal():

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        ip_publica = request.form.get('ip_publica')
        ip_rango = request.form.get('ip_rango')

        if not nombre:
            flash("El nombre es obligatorio", "danger")
            return redirect(url_for('sucursales.nueva_sucursal'))

        sucursal = Sucursal(
            empresa_id=current_user.empresa_id,
            nombre=nombre,
            ip_publica=ip_publica or None,
            ip_rango=ip_rango or None,
            activa=True
        )

        db.session.add(sucursal)
        db.session.commit()

        registrar_evento(
            "CREAR",
            "SUCURSAL",
            f"Sucursal creada: {nombre}"
        )

        flash("Sucursal creada correctamente", "success")
        return redirect(url_for('sucursales.lista_sucursales'))

    return render_template('sucursal_form.html')

# =========================
# ACTIVAR / DESACTIVAR
# =========================
@sucursales_bp.route('/toggle/<int:id>')
@login_required
@solo_admin
def toggle_sucursal(id):

    sucursal = Sucursal.query.filter_by(
        id=id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    sucursal.activa = not sucursal.activa
    db.session.commit()

    estado = "activada" if sucursal.activa else "desactivada"

    registrar_evento(
        "EDITAR",
        "SUCURSAL",
        f"Sucursal {estado}: {sucursal.nombre}"
    )

    flash(f"Sucursal {estado} correctamente", "info")

    return redirect(url_for('sucursales.lista_sucursales'))


# =========================
# EDITAR SUCURSAL
# =========================
@sucursales_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@solo_admin
def editar_sucursal(id):

    sucursal = Sucursal.query.filter_by(
        id=id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    if request.method == 'POST':

        nombre = request.form.get('nombre')
        ip_publica = request.form.get('ip_publica')
        ip_rango = request.form.get('ip_rango')

        if not nombre:
            flash("El nombre es obligatorio", "danger")
            return redirect(url_for('sucursales.editar_sucursal', id=id))

        sucursal.nombre = nombre
        sucursal.ip_publica = ip_publica or None
        sucursal.ip_rango = ip_rango or None

        db.session.commit()

        registrar_evento(
            "EDITAR",
            "SUCURSAL",
            f"Sucursal editada: {sucursal.nombre}"
        )

        flash("Sucursal actualizada correctamente", "success")
        return redirect(url_for('sucursales.lista_sucursales'))

    return render_template(
        'sucursal_form.html',
        sucursal=sucursal
    )


@sucursales_bp.route('/<int:id>/crear_kiosco')
@login_required
@solo_admin
def crear_kiosco(id):

    sucursal = Sucursal.query.filter_by(
        id=id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    token = secrets.token_urlsafe(16)

    kiosco = Kiosco(
        empresa_id=current_user.empresa_id,
        sucursal_id=sucursal.id,
        token=token
    )

    db.session.add(kiosco)
    db.session.commit()

    flash(f"Kiosco listo: {request.host_url}kiosco/{token}", "success")


    return redirect(url_for('sucursales.lista_sucursales'))