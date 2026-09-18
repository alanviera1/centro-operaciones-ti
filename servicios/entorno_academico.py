import json

from flask import current_app
from modelos import ArchivoAcademico, Auditoria, Evento, Incidente, Servicio, ahora, bd
from servicios.auditoria import usuario_actual

TABLAS_OPERATIVAS = ('incidentes', 'eventos', 'acciones_incidente', 'interrupciones', 'auditoria')


def restablecer_entorno(servicio):
    if not current_app.config['ENTORNO_ACADEMICO']:
        raise ValueError('El restablecimiento solo está disponible en el entorno académico.')
    bd.session.execute(bd.select(Servicio.id_servicio).where(Servicio.id_servicio == servicio.id_servicio).with_for_update())
    bd.session.flush()
    # Evita escrituras concurrentes mientras se copia y se vacía la operación.
    bd.session.execute(bd.text('LOCK TABLE incidentes, eventos, acciones_incidente, interrupciones, auditoria IN ACCESS EXCLUSIVE MODE'))
    externo = bd.session.scalar(bd.select(Incidente.id_incidente).where(Incidente.es_simulacion.is_(False)).limit(1))
    evento_externo = bd.session.scalar(bd.select(Evento.id_evento).where(Evento.es_simulacion.is_(False)).limit(1))
    if externo or evento_externo or bd.session.scalar(bd.select(bd.func.count()).select_from(Servicio)) != 1:
        raise ValueError('Solo se puede restablecer una instalación con un servicio y datos exclusivamente académicos.')
    contenido = {}
    for tabla in (*TABLAS_OPERATIVAS, 'componentes'):
        filas = bd.session.execute(bd.text(f'SELECT * FROM {tabla} ORDER BY 1')).mappings().all()
        contenido[tabla] = [dict(fila) for fila in filas]
    contenido['usuarios'] = [dict(fila) for fila in bd.session.execute(
        bd.text('SELECT id_usuario, nombre, rol FROM usuarios ORDER BY id_usuario')).mappings()]
    contenido['motivo'] = 'Fin del ciclo académico. Los estados y tiempos se conservan tal como estaban al restablecer.'
    contenido = json.loads(json.dumps(contenido, default=str))
    usuario = usuario_actual()
    archivo = ArchivoAcademico(id_servicio=servicio.id_servicio,
                              id_usuario=usuario.id_usuario if usuario else None, contenido=contenido)
    bd.session.add(archivo)
    bd.session.flush()
    # La copia y TRUNCATE/RESTART pertenecen a la misma transacción PostgreSQL.
    bd.session.execute(bd.text('TRUNCATE TABLE eventos, acciones_incidente, interrupciones, incidentes, auditoria RESTART IDENTITY'))
    bd.session.execute(bd.text('ALTER SEQUENCE secuencia_codigo_incidente RESTART WITH 1'))
    for objeto in list(bd.session.identity_map.values()):
        if objeto.__tablename__ in TABLAS_OPERATIVAS:
            bd.session.expunge(objeto)
    for componente in servicio.componentes:
        componente.estado = 'OPERATIVO'
    servicio.estado = 'OPERATIVO'
    bd.session.add(Auditoria(id_usuario=usuario.id_usuario if usuario else None,
        accion='ENTORNO_RESTABLECIDO', entidad='archivo_academico', referencia=str(archivo.id_archivo)))
    return len(contenido['incidentes'])
