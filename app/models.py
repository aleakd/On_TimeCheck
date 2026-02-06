from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
db = SQLAlchemy()


# =========================
# EMPRESA
# =========================
class Empresa(db.Model):
    __tablename__ = 'empresa'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    activa = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    empleados = db.relationship('Empleado', backref='empresa', lazy=True)
    asistencias = db.relationship('Asistencia', backref='empresa', lazy=True)

    def __repr__(self):
        return f'<Empresa {self.nombre}>'

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
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

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

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    empresa = db.relationship('Empresa', backref='usuarios')

    def __repr__(self):
        return f'<Usuario {self.email}>'
