from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import Sequence, select
from werkzeug.security import check_password_hash, generate_password_hash

bd = SQLAlchemy()
secuencia_codigo = Sequence('secuencia_codigo_incidente', metadata=bd.metadata)


def ahora():
    return datetime.now(timezone.utc)


def generar_codigo(contexto):
    consecutivo = contexto.connection.execute(select(secuencia_codigo.next_value())).scalar_one()
    if consecutivo > 9999:
        raise ValueError('La secuencia de códigos alcanzó el límite de cuatro dígitos.')
    fecha = contexto.get_current_parameters().get('fecha_inicio') or ahora()
    return f'INC-{fecha.astimezone(ZoneInfo("America/Lima")).year}-{consecutivo:04d}'


class Usuario(UserMixin, bd.Model):
    __tablename__ = 'usuarios'
    id_usuario = bd.Column(bd.Integer, primary_key=True)
    nombre = bd.Column(bd.String(100), nullable=False)
    correo = bd.Column(bd.String(180), nullable=False, unique=True)
    contrasena_hash = bd.Column(bd.String(255), nullable=False)
    rol = bd.Column(bd.String(15), nullable=False)
    activo = bd.Column(bd.Boolean, nullable=False, default=True)
    fecha_creacion = bd.Column(bd.DateTime(timezone=True), nullable=False, default=ahora)
    intentos_fallidos = bd.Column(bd.Integer, nullable=False, default=0)
    bloqueado_hasta = bd.Column(bd.DateTime(timezone=True))
    __table_args__ = (
        bd.CheckConstraint("rol IN ('OPERADOR','SUPERVISOR')"),
        bd.CheckConstraint('intentos_fallidos >= 0'),
        bd.CheckConstraint('correo = lower(correo)'),
    )

    def get_id(self):
        return str(self.id_usuario)

    @property
    def is_active(self):
        return self.activo

    def establecer_contrasena(self, contrasena):
        if len(contrasena) < 12 or len(contrasena) > 128:
            raise ValueError('La contraseña debe tener entre 12 y 128 caracteres.')
        self.contrasena_hash = generate_password_hash(contrasena, method='scrypt')

    def verificar_contrasena(self, contrasena):
        return check_password_hash(self.contrasena_hash, contrasena)


class Auditoria(bd.Model):
    __tablename__ = 'auditoria'
    id_auditoria = bd.Column(bd.Integer, primary_key=True)
    id_usuario = bd.Column(bd.Integer, bd.ForeignKey('usuarios.id_usuario'))
    accion = bd.Column(bd.String(60), nullable=False)
    entidad = bd.Column(bd.String(50), nullable=False)
    referencia = bd.Column(bd.String(120))
    fecha_hora = bd.Column(bd.DateTime(timezone=True), nullable=False, default=ahora, index=True)
    usuario = bd.relationship('Usuario')


class Servicio(bd.Model):
    __tablename__ = 'servicios'
    id_servicio = bd.Column(bd.Integer, primary_key=True)
    nombre = bd.Column(bd.String(120), nullable=False, unique=True)
    descripcion = bd.Column(bd.Text, nullable=False)
    sla_objetivo = bd.Column(bd.Numeric(5, 2), nullable=False, default=99.90)
    estado = bd.Column(bd.String(35), nullable=False, default='OPERATIVO')
    componentes = bd.relationship('Componente', back_populates='servicio', order_by='Componente.id_componente')
    __table_args__ = (
        bd.CheckConstraint('sla_objetivo > 0 AND sla_objetivo <= 100'),
        bd.CheckConstraint("estado IN ('OPERATIVO','ADVERTENCIA','CAIDO','OPERATIVO_CON_RESPALDO')"),
    )


class ArchivoAcademico(bd.Model):
    __tablename__ = 'archivo_academico'
    id_archivo = bd.Column(bd.Integer, primary_key=True)
    id_servicio = bd.Column(bd.Integer, bd.ForeignKey('servicios.id_servicio'), nullable=False)
    id_usuario = bd.Column(bd.Integer, bd.ForeignKey('usuarios.id_usuario'))
    fecha_hora = bd.Column(bd.DateTime(timezone=True), nullable=False, default=ahora)
    contenido = bd.Column(bd.JSON, nullable=False)
    usuario = bd.relationship('Usuario')


class Componente(bd.Model):
    __tablename__ = 'componentes'
    id_componente = bd.Column(bd.Integer, primary_key=True)
    id_servicio = bd.Column(bd.Integer, bd.ForeignKey('servicios.id_servicio'), nullable=False)
    nombre = bd.Column(bd.String(120), nullable=False)
    tipo = bd.Column(bd.String(35), nullable=False)
    estado = bd.Column(bd.String(25), nullable=False, default='OPERATIVO')
    servicio = bd.relationship('Servicio', back_populates='componentes')
    __table_args__ = (
        bd.UniqueConstraint('id_servicio', 'tipo'),
        bd.CheckConstraint("estado IN ('OPERATIVO','ADVERTENCIA','CAIDO','RESPALDO_ACTIVO')"),
    )


class Incidente(bd.Model):
    __tablename__ = 'incidentes'
    id_incidente = bd.Column(bd.Integer, primary_key=True)
    codigo_incidente = bd.Column(bd.String(35), nullable=False, unique=True, default=generar_codigo)
    es_simulacion = bd.Column(bd.Boolean, nullable=False, default=False)
    archivado = bd.Column(bd.Boolean, nullable=False, default=False)
    id_responsable = bd.Column(bd.Integer, bd.ForeignKey('usuarios.id_usuario'))
    responsable = bd.relationship('Usuario')
    id_servicio = bd.Column(bd.Integer, bd.ForeignKey('servicios.id_servicio'), nullable=False)
    id_componente = bd.Column(bd.Integer, bd.ForeignKey('componentes.id_componente'), nullable=False)
    titulo = bd.Column(bd.String(180), nullable=False)
    descripcion = bd.Column(bd.Text, nullable=False)
    impacto = bd.Column(bd.Integer, nullable=False)
    urgencia = bd.Column(bd.Integer, nullable=False)
    prioridad = bd.Column(bd.String(15), nullable=False)
    estado = bd.Column(bd.String(20), nullable=False, default='ABIERTO')
    usuarios_afectados = bd.Column(bd.Integer, nullable=False, default=0)
    operaciones_fallidas = bd.Column(bd.Integer, nullable=False, default=0)
    perdida_estimada = bd.Column(bd.Numeric(14, 2), nullable=False, default=0)
    fecha_inicio = bd.Column(bd.DateTime(timezone=True), nullable=False, default=ahora)
    fecha_recuperacion = bd.Column(bd.DateTime(timezone=True))
    fecha_resolucion = bd.Column(bd.DateTime(timezone=True))
    fecha_cierre = bd.Column(bd.DateTime(timezone=True))
    demostracion = bd.Column(bd.Boolean, nullable=False, default=False)
    componente = bd.relationship('Componente')
    eventos = bd.relationship('Evento', back_populates='incidente', order_by='Evento.fecha_hora')
    acciones = bd.relationship('AccionIncidente', back_populates='incidente', order_by='AccionIncidente.fecha_hora')
    interrupciones = bd.relationship('Interrupcion', back_populates='incidente')
    __table_args__ = (
        bd.CheckConstraint('impacto BETWEEN 1 AND 3 AND urgencia BETWEEN 1 AND 3'),
        bd.CheckConstraint('usuarios_afectados >= 0 AND operaciones_fallidas >= 0 AND perdida_estimada >= 0'),
        bd.CheckConstraint("estado IN ('ABIERTO','EN_PROCESO','RESUELTO','CERRADO')"),
        bd.CheckConstraint("prioridad IN ('BAJA','MEDIA','ALTA','CRITICA')"),
        bd.CheckConstraint('fecha_recuperacion IS NULL OR fecha_recuperacion >= fecha_inicio'),
        bd.CheckConstraint('fecha_resolucion IS NULL OR fecha_resolucion >= fecha_recuperacion'),
        bd.CheckConstraint('fecha_cierre IS NULL OR fecha_cierre >= fecha_resolucion'),
        bd.Index('un_incidente_activo_por_componente', 'id_componente', unique=True,
                 postgresql_where=bd.text("estado IN ('ABIERTO','EN_PROCESO')")),
    )

    @property
    def numero(self):
        return self.codigo_incidente


class Evento(bd.Model):
    __tablename__ = 'eventos'
    id_evento = bd.Column(bd.Integer, primary_key=True)
    es_simulacion = bd.Column(bd.Boolean, nullable=False, default=False)
    archivado = bd.Column(bd.Boolean, nullable=False, default=False)
    id_componente = bd.Column(bd.Integer, bd.ForeignKey('componentes.id_componente'), nullable=False)
    id_incidente = bd.Column(bd.Integer, bd.ForeignKey('incidentes.id_incidente'))
    tipo = bd.Column(bd.String(50), nullable=False)
    descripcion = bd.Column(bd.Text, nullable=False)
    nivel = bd.Column(bd.String(15), nullable=False)
    fecha_hora = bd.Column(bd.DateTime(timezone=True), nullable=False, default=ahora, index=True)
    atendido = bd.Column(bd.Boolean, nullable=False, default=False)
    componente = bd.relationship('Componente')
    incidente = bd.relationship('Incidente', back_populates='eventos')
    __table_args__ = (bd.CheckConstraint("nivel IN ('INFORMATIVO','ADVERTENCIA','CRITICO')"),)


class AccionIncidente(bd.Model):
    __tablename__ = 'acciones_incidente'
    id_accion = bd.Column(bd.Integer, primary_key=True)
    id_usuario = bd.Column(bd.Integer, bd.ForeignKey('usuarios.id_usuario'))
    usuario = bd.relationship('Usuario')
    id_incidente = bd.Column(bd.Integer, bd.ForeignKey('incidentes.id_incidente'), nullable=False)
    accion = bd.Column(bd.String(120), nullable=False)
    resultado = bd.Column(bd.Text, nullable=False)
    fecha_hora = bd.Column(bd.DateTime(timezone=True), nullable=False, default=ahora)
    incidente = bd.relationship('Incidente', back_populates='acciones')


class Interrupcion(bd.Model):
    __tablename__ = 'interrupciones'
    id_interrupcion = bd.Column(bd.Integer, primary_key=True)
    id_servicio = bd.Column(bd.Integer, bd.ForeignKey('servicios.id_servicio'), nullable=False)
    id_incidente = bd.Column(bd.Integer, bd.ForeignKey('incidentes.id_incidente'), nullable=False)
    minutos_caida = bd.Column(bd.Numeric(12, 4), nullable=False, default=0)
    fecha_inicio = bd.Column(bd.DateTime(timezone=True), nullable=False)
    fecha_fin = bd.Column(bd.DateTime(timezone=True))
    incidente = bd.relationship('Incidente', back_populates='interrupciones')
    __table_args__ = (
        bd.CheckConstraint('minutos_caida >= 0'),
        bd.CheckConstraint('fecha_fin IS NULL OR fecha_fin >= fecha_inicio'),
        bd.UniqueConstraint('id_incidente'),
    )
