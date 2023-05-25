from flask_sqlalchemy import SQLAlchemy
from marshmallow import fields
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

import enum
import datetime

db = SQLAlchemy()


class ExtensionFinal(enum.Enum):
    ZIP = 1
    TAR_GZ = 2
    TAR_BZ2 = 3


class EstadoTarea(enum.Enum):
    DISPONIBLE = 1
    NO_DISPONIBLE = 2


class EstadoConversion(enum.Enum):
    UPLOADED = 1
    PROCESSING = 2
    COMPLETED = 3
    FAILED = 4


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_nombre = db.Column(db.String(64), unique=True, nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    contrasena_encriptada = db.Column(db.String(128))
    tareas = db.relationship('TareaConversion', backref='usuario', lazy=True, cascade='all, delete, delete-orphan')

class TareaConversion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_archivo = db.Column(db.String(120), nullable=False)
    extension_final = db.Column(db.Enum(ExtensionFinal))
    estado_tarea = db.Column(db.Enum(EstadoTarea), nullable=False)
    estado_conversion = db.Column(db.Enum(EstadoConversion), default=EstadoConversion.UPLOADED)
    fecha_creacion = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    fecha_modificacion = db.Column(db.DateTime, onupdate=datetime.datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))

class EnumADiccionario(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        return {'llave': value.name, 'valor': value.value}


class UsuarioSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Usuario
        include_relationships = True
        include_fk = True
        load_instance = True

    id = fields.String()
    usuario_nombre = fields.String()
    contrasena = fields.String()
    correo = fields.String()


class TareaConversionSchema(SQLAlchemyAutoSchema):
    extension_final = EnumADiccionario(attribute=('extension_final'))
    estado_tarea = EnumADiccionario(attribute='estado_tarea')
    estado_conversion = EnumADiccionario(attribute='estado_conversion')

    class Meta:
        model = TareaConversion
        include_relationships = True
        include_fk = True
        load_instance = True
    
    data = fields.Raw(load_only=True)
