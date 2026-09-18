from servicios.gestor_incidentes import obtener_respaldo

CONCIERTOS = [('luz', 'Luces de Lima', 'Pop · Arena del Pacífico'),
              ('andes', 'Sonidos de los Andes', 'Fusión · Parque Horizonte'),
              ('noche', 'Noche del Sur', 'Rock · Teatro Aurora')]

DETALLES_CONCIERTOS = {
    'luz': dict(dia='24', mes='OCT', hora='20:00', genero='POP EN VIVO', precio='130', estilo='luz', frase='Una ciudad. Mil luces.'),
    'andes': dict(dia='07', mes='NOV', hora='18:30', genero='FUSIÓN & RAÍCES', precio='95', estilo='andes', frase='El origen suena distinto.'),
    'noche': dict(dia='21', mes='NOV', hora='21:00', genero='ROCK AL AIRE LIBRE', precio='150', estilo='noche', frase='Hasta la última canción.'),
}


def representar_servicio(servicio):
    componentes = {c.tipo: c for c in servicio.componentes}

    def disponible(tipo):
        componente = componentes[tipo]
        respaldo = obtener_respaldo(componente)
        return componente.estado != 'CAIDO' or bool(respaldo and respaldo.estado == 'RESPALDO_ACTIVO')

    web = disponible('WEB')
    base = disponible('BD')
    pagos = disponible('PAGOS')
    autenticacion = disponible('AUTENTICACION')
    contingencia = any(c.estado == 'RESPALDO_ACTIVO' for c in componentes.values())
    if not web:
        mensaje = 'Servicio no disponible: el servidor web está caído.'
    elif not base:
        mensaje = 'Reservas temporalmente no disponibles: la base de datos está caída.'
    elif not pagos:
        mensaje = 'Pagos temporalmente no disponibles.'
    elif not autenticacion:
        mensaje = 'Inicio de sesión temporalmente no disponible.'
    elif contingencia:
        mensaje = 'Servicio operativo mediante contingencia.'
    elif any(c.estado == 'ADVERTENCIA' for c in componentes.values()):
        mensaje = 'Servicio disponible con advertencias de rendimiento.'
    else:
        mensaje = 'Servicio operativo.'
    web_principal = componentes['WEB'].estado
    estado_general = 'error' if not (web and base and pagos and autenticacion) else 'aviso' if contingencia or servicio.estado == 'ADVERTENCIA' else 'bien'
    def descripcion(tipo):
        componente = componentes[tipo]
        respaldo = obtener_respaldo(componente)
        if respaldo and respaldo.estado == 'RESPALDO_ACTIVO':
            return 'Principal caído · respaldo activo' if componente.estado == 'CAIDO' else 'Respaldo activo'
        return {'OPERATIVO': 'Operativo', 'ADVERTENCIA': 'Con lentitud', 'CAIDO': 'No disponible'}.get(componente.estado, 'Contingencia activa')
    if not web:
        motivo_compra = 'La plataforma está temporalmente fuera de servicio. Vuelve a intentarlo cuando se restaure la conexión.'
    elif not base:
        motivo_compra = 'No podemos consultar las entradas en este momento. No se ha reservado ni cobrado nada.'
    elif not autenticacion:
        motivo_compra = 'El acceso de clientes no está disponible. La compra simulada se habilitará al recuperar autenticación.'
    else:
        motivo_compra = 'Nuestro proveedor de pagos no responde. Tu selección no ha generado ningún cargo.'
    return dict(mensaje=mensaje, puede_iniciar=web and base and autenticacion,
                puede_comprar=web and base and pagos and autenticacion,
                pagos=pagos, autenticacion=autenticacion, contingencia=contingencia,
                estado=servicio.estado, disponible=web and base, tono=estado_general,
                web_principal=web_principal, web=web, texto_web=descripcion('WEB'),
                texto_pagos=descripcion('PAGOS'), texto_autenticacion=descripcion('AUTENTICACION'),
                motivo_compra=motivo_compra,
                motivo_acceso='El acceso de clientes está interrumpido. No afecta a tu sesión administrativa del Centro de Operaciones TI.' if not autenticacion else mensaje,
                titulo_aviso='Volvemos en un momento' if not web else 'Algunas operaciones están pausadas' if estado_general == 'error' else 'Seguimos contigo mediante contingencia' if contingencia else 'Todo listo para tu próxima experiencia')
