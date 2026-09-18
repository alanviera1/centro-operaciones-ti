from datetime import timedelta

from flask import current_app

from modelos import Evento, Incidente, Interrupcion, ahora, bd
from servicios.gestor_incidentes import calcular_prioridad, registrar_accion

MINUTOS_CORRELACION = 5
CRITICOS_NECESARIOS = 1
ADVERTENCIAS_NECESARIAS = 3
REGLA_CORRELACION = ('Un evento crítico o tres advertencias del mismo componente en cinco minutos '
                    'generan un incidente. Se consideran eventos sin atender, no archivados y aún sin incidente.')


def eventos_pendientes(componente):
    return bd.session.scalars(bd.select(Evento).where(
        Evento.id_componente == componente.id_componente,
        Evento.id_incidente.is_(None), Evento.atendido.is_(False),
        Evento.archivado.is_(False),
        Evento.fecha_hora >= ahora() - timedelta(minutes=MINUTOS_CORRELACION),
    ).order_by(Evento.fecha_hora)).all()


def correlacionar_eventos(componente, escenario, impacto, urgencia, minutos):
    eventos = eventos_pendientes(componente)
    criticos = 0
    advertencias = 0
    for evento in eventos:
        if evento.nivel == 'CRITICO':
            criticos += 1
        elif evento.nivel == 'ADVERTENCIA':
            advertencias += 1
    incidente = bd.session.scalar(bd.select(Incidente).where(
        Incidente.id_componente == componente.id_componente,
        Incidente.estado.in_(['ABIERTO', 'EN_PROCESO', 'RESUELTO']),
        Incidente.archivado.is_(False),
    ))
    if incidente and incidente.fecha_recuperacion:
        raise ValueError('Resuelve y cierra el incidente recuperado antes de volver a simular esta falla.')
    if not incidente and criticos < CRITICOS_NECESARIOS and advertencias < ADVERTENCIAS_NECESARIAS:
        return None
    if not incidente:
        incidente = Incidente(
            id_servicio=componente.id_servicio, componente=componente,
            es_simulacion=True,
            titulo=escenario['titulo'], descripcion=escenario['descripcion'],
            impacto=impacto, urgencia=urgencia, prioridad=calcular_prioridad(impacto, urgencia),
            usuarios_afectados=escenario['usuarios'], operaciones_fallidas=escenario['operaciones'],
            perdida_estimada=escenario['operaciones'] * current_app.config['VALOR_PROMEDIO_ENTRADA'],
        )
        bd.session.add(incidente)
        bd.session.flush()
        registrar_accion(incidente, 'Incidente generado',
                         f'{REGLA_CORRELACION} Eventos observados — críticos: {criticos}; advertencias: {advertencias}. '
                         f'Impacto {impacto} × urgencia {urgencia} = {impacto * urgencia}: {incidente.prioridad}.')
    else:
        incidente.impacto = max(incidente.impacto, impacto)
        incidente.urgencia = max(incidente.urgencia, urgencia)
        incidente.prioridad = calcular_prioridad(incidente.impacto, incidente.urgencia)
        incidente.usuarios_afectados = max(incidente.usuarios_afectados, escenario['usuarios'])
        incidente.operaciones_fallidas = max(incidente.operaciones_fallidas, escenario['operaciones'])
        incidente.perdida_estimada = max(incidente.perdida_estimada,
                                        escenario['operaciones'] * current_app.config['VALOR_PROMEDIO_ENTRADA'])
        if escenario['interrumpe']:
            incidente.titulo = escenario['titulo']
            incidente.descripcion = escenario['descripcion']
        registrar_accion(incidente, 'Eventos correlacionados',
                         'Eventos asociados a la falla activa. Se conserva el mayor impacto y urgencia; '
                         'los usuarios y operaciones se actualizan al máximo observado, sin sumarlos otra vez.')
    if escenario['interrumpe'] and not incidente.interrupciones:
        bd.session.add(Interrupcion(
            id_servicio=componente.id_servicio, incidente=incidente,
            fecha_inicio=ahora() - timedelta(minutes=minutos), minutos_caida=minutos,
        ))
    for evento in eventos:
        evento.incidente = incidente
    return incidente
