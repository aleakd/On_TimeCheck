from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy.sql import func

db = SQLAlchemy()


# =========================
# EMPRESA
# =========================
class Empresa(db.Model):
    __tablename__ = 'empresa'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    activa = db.Column(db.Boolean, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now()
    )
    # 🔐 SEGURIDAD RED
    #ip_publica = db.Column(db.String(50), nullable=True)
    #ip_rango = db.Column(db.String(50), nullable=True)

    usuarios = db.relationship('Usuario', backref='empresa', lazy=True)
    empleados = db.relationship('Empleado', backref='empresa', lazy=True)
    asistencias = db.relationship('Asistencia', backref='empresa', lazy=True)

    def __repr__(self):
        return f'<Empresa {self.nombre}>'

# =========================
# SUCURSAL
# =========================
class Sucursal(db.Model):
    __tablename__ = 'sucursal'

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(
        db.Integer,
        db.ForeignKey('empresa.id'),
        nullable=False
    )
    nombre = db.Column(db.String(100), nullable=False)
    ip_publica = db.Column(db.String(50), nullable=True)
    ip_rango = db.Column(db.String(50), nullable=True)
    activa = db.Column(db.Boolean, default=True)

    empresa = db.relationship(
        'Empresa',
        backref=db.backref('sucursales', lazy=True)
    )
    empleados = db.relationship(
        'Empleado',
        back_populates='sucursal',
        lazy=True
    )


# =========================
# EMPLEADO
# =========================
class Empleado(db.Model):
    __tablename__ = 'empleado'
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(
        db.Integer,
        db.ForeignKey('empresa.id'),
        nullable=False
    )
    dni = db.Column(db.String(20), nullable=False)
    apellido = db.Column(db.String(50), nullable=False)
    nombre = db.Column(db.String(50), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    asistencias = db.relationship('Asistencia', backref='empleado', lazy=True)
    sucursal_id = db.Column(
        db.Integer,
        db.ForeignKey('sucursal.id'),
        nullable=False
    )
    sucursal = db.relationship(
        'Sucursal',
        back_populates='empleados'
    )
    turno_inicio = db.Column(db.Time, nullable=True)
    turno_fin = db.Column(db.Time, nullable=True)
    tolerancia_minutos = db.Column(
        db.Integer,
        default=15
    )

    def __repr__(self):
        return f'<Empleado {self.apellido}, {self.nombre}>'

# =========================
# ASISTENCIA
# =========================
class Asistencia(db.Model):
    __tablename__ = 'asistencia'
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(
        db.Integer,
        db.ForeignKey('empresa.id'),
        nullable=False
    )
    empleado_id = db.Column(
        db.Integer,
        db.ForeignKey('empleado.id'),
        nullable=False
    )
    tipo = db.Column(
        db.String(10),
        nullable=False
    )  # INGRESO / SALIDA

    # La actividad pertenece al BLOQUE DE TRABAJO (se define en el ingreso)
    actividad = db.Column(
        db.String(50),
        nullable=True
    )

    fecha_hora = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    sucursal_id = db.Column(
        db.Integer,
        db.ForeignKey('sucursal.id'),
        nullable=False
    )

    sucursal = db.relationship('Sucursal')

    def __repr__(self):
        return f'<Asistencia {self.tipo} - Empleado {self.empleado_id}>'

# =========================
# USUARIO (BASE PARA FUTURO)
# =========================
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(
        db.Integer,
        db.ForeignKey('empresa.id'),
        nullable=False
    )
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(
        db.String(20),
        default='empleado'
    )  # admin / supervisor / empleado
    activo = db.Column(db.Boolean, default=True)
    empleado_id = db.Column(db.Integer, db.ForeignKey('empleado.id'), nullable=True)
    empleado = db.relationship('Empleado')
    created_at = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now()
    )

    def __repr__(self):
        return f'<Usuario {self.email}>'

# =========================
# AUDITORÍA DEL SISTEMA
# ========================
class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(
        db.Integer,
        db.ForeignKey('empresa.id'),
        nullable=False
    )
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey('usuario.id'),
        nullable=True
    )
    accion = db.Column(db.String(100), nullable=False)
    entidad = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    ip = db.Column(db.String(50), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    usuario = db.relationship('Usuario')
    def __repr__(self):
        return f'<AuditLog {self.accion} - {self.entidad}>'


# =========================
# AUDITORÍA DEL SISTEMA
# ========================
class HorarioEmpleado(db.Model):
    __tablename__ = "horario_empleado"

    id = db.Column(db.Integer, primary_key=True)

    empleado_id = db.Column(
        db.Integer,
        db.ForeignKey('empleado.id'),
        nullable=False
    )

    fecha = db.Column(db.Date, nullable=False)

    hora_inicio = db.Column(db.Time, nullable=True)
    hora_fin = db.Column(db.Time, nullable=True)

    tipo = db.Column(db.String(20), nullable=False)
    # TRABAJA / FRANCO / LICENCIA / FERIADO

    observacion = db.Column(db.String(200), nullable=True)

    empleado = db.relationship("Empleado")