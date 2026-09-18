from modelos import AccionIncidente, Evento, ahora, bd
from servicios.auditoria import registrar_auditoria, usuario_actual

RESPALDOS = {'PAGOS': 'PAGOS_ALTERNATIVA', 'WEB': 'WEB_RESPALDO'}


def calcular_prioridad(impacto, urgencia):
    if impacto not in (1, 2, 3) or urgencia not in (1, 2, 3):
        raise ValueError('Impacto y urgencia deben estar entre 1 y 3.')
    valor = impacto * urgencia
    if valor <= 2:
        return 'BAJA'
    if valor <= 4:
        return 'MEDIA'
    if valor == 6:
        return 'ALTA'
    return 'CRITICA'


def registrar_accion(incidente, accion, resultado):
    usuario = usuario_actual()
    bd.session.add(AccionIncidente(incidente=incidente, accion=accion, resultado=resultado, usuario=usuario))
    registrar_auditoria(accion, 'incidentes', incidente.codigo_incidente, usuario)


def obtener_respaldo(componente):
    tipo = RESPALDOS.get(componente.tipo)
    for candidato in componente.servicio.componentes:
        if candidato.tipo == tipo:
            return candidato
    return None


def actualizar_servicio(servicio):
    caido = False
    advertencia = False
    respaldo_activo = False
    for componente in servicio.componentes:
        if componente.estado == 'CAIDO':
            respaldo = obtener_respaldo(componente)
            if not respaldo or respaldo.estado != 'RESPALDO_ACTIVO':
                caido = True
        if componente.estado == 'ADVERTENCIA':
            advertencia = True
        if componente.estado == 'RESPALDO_ACTIVO':
            respaldo_activo = True
    if caido:
        servicio.estado = 'CAIDO'
    elif advertencia:
        servicio.estado = 'ADVERTENCIA'
    elif respaldo_activo:
        servicio.estado = 'OPERATIVO_CON_RESPALDO'
    else:
        servicio.estado = 'OPERATIVO'


def registrar_recuperacion(incidente):
    momento = ahora()
    incidente.fecha_recuperacion = momento
    for interrupcion in incidente.interrupciones:
        if interrupcion.fecha_fin is None:
            interrupcion.fecha_fin = momento
            interrupcion.minutos_caida = (momento - interrupcion.fecha_inicio).total_seconds() / 60
    for evento in incidente.eventos:
        evento.atendido = True
    bd.session.add(Evento(componente=incidente.componente, incidente=incidente,
                         tipo='RECUPERACION', descripcion='Servicio recuperado mediante una acción simulada.',
                         nivel='INFORMATIVO', atendido=True, es_simulacion=incidente.es_simulacion))


def acciones_disponibles(incidente):
    if incidente.archivado:
        return []
    if incidente.estado in ('RESUELTO', 'CERRADO'):
        return [('cerrar', 'Cerrar y normalizar servicio')] if incidente.estado == 'RESUELTO' else []
    acciones = []
    if incidente.estado == 'ABIERTO':
        acciones.append(('iniciar', 'Iniciar atención'))
    elif incidente.estado == 'EN_PROCESO' and not incidente.fecha_recuperacion:
        if incidente.componente.tipo == 'PAGOS':
            acciones.append(('activar_respaldo', 'Activar pasarela alternativa'))
        if incidente.componente.tipo == 'WEB':
            acciones.append(('activar_respaldo', 'Activar servidor de respaldo'))
        
        if incidente.componente.tipo == 'WEB':
            etiqueta_reiniciar = 'Reiniciar servidor web'
        elif incidente.componente.tipo == 'AUTENTICACION':
            etiqueta_reiniciar = 'Reiniciar servicio de autenticación'
        elif incidente.componente.tipo == 'BD':
            etiqueta_reiniciar = 'Restablecer servicio de base de datos'
        elif incidente.componente.tipo == 'PAGOS':
            etiqueta_reiniciar = 'Reintentar pasarela principal'
        else:
            etiqueta_reiniciar = f'Reiniciar {incidente.componente.nombre.lower()}'
            
        acciones.append(('reiniciar', etiqueta_reiniciar))
        usuario = usuario_actual()
        if usuario and usuario.rol == 'OPERADOR' and not any(
                registro.accion == 'Escalar incidente' for registro in incidente.acciones):
            acciones.append(('escalar', 'Escalar incidente'))
    elif incidente.estado == 'EN_PROCESO' and incidente.fecha_recuperacion:
        acciones.append(('resolver', 'Marcar como resuelto'))
    return acciones


def ejecutar_accion(incidente, accion):
    usuario = usuario_actual()
    if accion == 'cerrar' and (not usuario or usuario.rol != 'SUPERVISOR'):
        raise PermissionError('Solo un supervisor puede cerrar incidentes.')
    if accion == 'escalar' and (not usuario or usuario.rol != 'OPERADOR'):
        raise PermissionError('Solo un operador puede escalar incidentes.')
    permitidas = dict(acciones_disponibles(incidente))
    if accion not in permitidas:
        raise ValueError('La acción no es válida para el estado actual del incidente.')
    componente = incidente.componente
    if usuario and not incidente.responsable:
        incidente.responsable = usuario
    if accion == 'iniciar':
        incidente.estado = 'EN_PROCESO'
        resultado = 'Atención iniciada. Se asignó la responsabilidad al operador de la acción.'
    elif accion == 'activar_respaldo':
        respaldo = obtener_respaldo(componente)
        if not respaldo or respaldo.estado != 'OPERATIVO':
            raise ValueError('El componente de respaldo no está disponible.')
        respaldo.estado = 'RESPALDO_ACTIVO'
        componente.estado = 'CAIDO'
        incidente.estado = 'EN_PROCESO'
        registrar_recuperacion(incidente)
        resultado = 'Servicio recuperado con respaldo. El componente principal sigue caído; se detuvo su interrupción.'
    elif accion == 'reiniciar':
        componente.estado = 'OPERATIVO'
        incidente.estado = 'EN_PROCESO'
        registrar_recuperacion(incidente)
        resultado = 'Reinicio simulado completado. Componente operativo e interrupción finalizada.'
    elif accion == 'escalar':
        resultado = 'Escalamiento académico registrado para el equipo de soporte. No se envían comunicaciones externas.'
    elif accion == 'resolver':
        incidente.estado = 'RESUELTO'
        incidente.fecha_resolucion = ahora()
        resultado = 'Recuperación verificada. Incidente resuelto y pendiente de cierre.'
    elif accion == 'cerrar':
        respaldo = obtener_respaldo(componente)
        if componente.estado != 'OPERATIVO':
            componente.estado = 'OPERATIVO'
            registrar_accion(incidente, 'Restaurar componente principal',
                             'Componente principal normalizado durante el cierre.')
        if respaldo and respaldo.estado == 'RESPALDO_ACTIVO':
            respaldo.estado = 'OPERATIVO'
            registrar_accion(incidente, 'Desactivar contingencia',
                             'Respaldo desactivado y disponible para nuevas incidencias.')
        incidente.estado = 'CERRADO'
        incidente.fecha_cierre = ahora()
        resultado = 'Servicio normalizado y cierre administrativo registrado. Se conserva la trazabilidad.'
    actualizar_servicio(componente.servicio)
    registrar_accion(incidente, permitidas[accion], resultado)
