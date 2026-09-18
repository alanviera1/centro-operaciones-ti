from datetime import timedelta

from flask import current_app

from modelos import Componente, Incidente, Interrupcion, ahora, bd


def calcular_disponibilidad(tiempo_acordado, tiempo_caido):
    if tiempo_acordado <= 0 or tiempo_caido < 0:
        raise ValueError('Los tiempos deben ser válidos y el período mayor que cero.')
    tiempo_caido = min(tiempo_caido, tiempo_acordado)
    return (tiempo_acordado - tiempo_caido) / tiempo_acordado * 100


def unir_intervalos(intervalos):
    if not intervalos:
        return 0.0
    intervalos = sorted(intervalos)
    inicio, fin = intervalos[0]
    segundos = 0.0
    for siguiente_inicio, siguiente_fin in intervalos[1:]:
        if siguiente_inicio <= fin:
            fin = max(fin, siguiente_fin)
        else:
            segundos += (fin - inicio).total_seconds()
            inicio, fin = siguiente_inicio, siguiente_fin
    segundos += (fin - inicio).total_seconds()
    return segundos / 60


def medir_servicio(servicio):
    fin = ahora()
    minutos = current_app.config['MINUTOS_PERIODO']
    inicio = fin - timedelta(minutes=minutos)
    interrupciones = bd.session.scalars(bd.select(Interrupcion).join(Interrupcion.incidente).where(
        Incidente.archivado.is_(False),
        Interrupcion.id_servicio == servicio.id_servicio,
        bd.or_(Interrupcion.fecha_fin.is_(None), Interrupcion.fecha_fin >= inicio),
    )).all()
    intervalos = []
    for interrupcion in interrupciones:
        desde = max(inicio, interrupcion.fecha_inicio)
        hasta = min(fin, interrupcion.fecha_fin or fin)
        if hasta > desde:
            intervalos.append((desde, hasta))
    caida = unir_intervalos(intervalos)
    disponibilidad = calcular_disponibilidad(minutos, caida)
    presupuesto = minutos * (1 - float(servicio.sla_objetivo) / 100)
    if disponibilidad < float(servicio.sla_objetivo):
        estado_sla = 'INCUMPLIDO'
    else:
        estado_sla = 'CUMPLIDO'
    en_riesgo = presupuesto > 0 and caida >= presupuesto * 0.8 and estado_sla == 'CUMPLIDO'
    filtro = (Incidente.id_servicio == servicio.id_servicio, Incidente.archivado.is_(False))
    abiertos = (*filtro, Incidente.estado.in_(['ABIERTO', 'EN_PROCESO']))
    cantidad_activos = bd.session.scalar(bd.select(bd.func.count()).select_from(Incidente).where(*abiertos))
    pendientes = bd.session.scalar(bd.select(bd.func.count()).select_from(Incidente).where(
        *filtro, Incidente.estado == 'RESUELTO'))
    activos = bd.session.scalars(bd.select(Incidente).where(*filtro, Incidente.estado != 'CERRADO')
        .order_by((Incidente.impacto * Incidente.urgencia).desc(), Incidente.fecha_inicio).limit(6)).all()
    usuarios = bd.session.scalar(bd.select(bd.func.coalesce(bd.func.sum(Incidente.usuarios_afectados), 0))
        .where(*abiertos, Incidente.fecha_recuperacion.is_(None)))
    cerrados = bd.session.scalar(bd.select(bd.func.count()).select_from(Incidente).where(
        *filtro, Incidente.estado == 'CERRADO'))
    duracion = bd.extract('epoch', Incidente.fecha_recuperacion - Incidente.fecha_inicio) / 60
    promedio = bd.session.scalar(bd.select(bd.func.coalesce(bd.func.avg(duracion), 0)).where(
        *filtro, Incidente.fecha_recuperacion >= inicio))
    por_prioridad = {'CRITICA': 0, 'ALTA': 0, 'MEDIA': 0, 'BAJA': 0}
    for prioridad, cantidad in bd.session.execute(bd.select(Incidente.prioridad, bd.func.count())
            .where(*filtro, Incidente.fecha_inicio >= inicio).group_by(Incidente.prioridad)):
        por_prioridad[prioridad] = cantidad
    por_componente = dict(bd.session.execute(bd.select(Componente.nombre, bd.func.count())
        .join(Incidente, Incidente.id_componente == Componente.id_componente)
        .where(*filtro, Incidente.fecha_inicio >= inicio).group_by(Componente.nombre)).all())
    return dict(disponibilidad=disponibilidad, caida=caida, estado_sla=estado_sla, en_riesgo=en_riesgo,
                presupuesto=presupuesto, restante=max(0, presupuesto - caida),
                activos=activos, cantidad_activos=cantidad_activos, pendientes=pendientes,
                cerrados=cerrados, usuarios=usuarios, promedio=promedio,
                por_prioridad=por_prioridad, por_componente=por_componente,
                minutos=minutos, inicio=inicio, fin=fin)
