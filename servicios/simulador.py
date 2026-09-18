from modelos import Componente, Evento, Incidente, bd
from servicios.gestor_eventos import correlacionar_eventos, eventos_pendientes, CRITICOS_NECESARIOS, ADVERTENCIAS_NECESARIAS
from servicios.gestor_incidentes import actualizar_servicio, obtener_respaldo, calcular_prioridad
from servicios.auditoria import registrar_auditoria

ESCENARIOS = {
    'latencia': dict(nombre='Latencia elevada', boton='Simular latencia elevada', tipo='WEB',
                    titulo='Latencia persistente en el servidor web',
                    descripcion='Reducción simulada de la calidad del servicio por tiempos de respuesta elevados.',
                    usuarios=95, operaciones=0, impacto=1, urgencia=2, interrumpe=False,
                    eventos=[('LATENCIA', 'Tiempo de respuesta superior a 3 segundos.', 'ADVERTENCIA')]),
    'pagos': dict(nombre='Caída de pasarela de pagos', boton='Simular caída de pagos', tipo='PAGOS',
                  titulo='Pasarela de pagos no disponible',
                  descripcion='El proveedor principal no responde y los clientes no pueden completar sus compras.',
                  usuarios=742, operaciones=186, impacto=3, urgencia=3, interrumpe=True,
                  eventos=[('LATENCIA', 'Tiempo de respuesta elevado en pagos.', 'ADVERTENCIA'),
                           ('PROVEEDOR', 'El proveedor de pagos no responde.', 'CRITICO'),
                           ('TRANSACCIONES', '186 transacciones rechazadas.', 'CRITICO')]),
    'servidor': dict(nombre='Caída del servidor web', boton='Simular caída del servidor', tipo='WEB',
                    titulo='Servidor web principal no disponible', descripcion='La plataforma de entradas no responde.',
                    usuarios=1200, operaciones=220, impacto=3, urgencia=3, interrumpe=True,
                    eventos=[('SERVIDOR', 'Servidor web no disponible.', 'CRITICO'),
                             ('CONEXIONES', 'Conexiones HTTP fallidas.', 'CRITICO')]),
    'base_datos': dict(nombre='Problema de base de datos', boton='Simular problema de base de datos', tipo='BD',
                      titulo='Base de datos con consultas bloqueadas',
                      descripcion='Bloqueo simulado de consultas que impide procesar reservas.',
                      usuarios=320, operaciones=60, impacto=2, urgencia=3, interrumpe=True,
                      eventos=[('CONSULTAS', 'Consultas con demora elevada.', 'ADVERTENCIA'),
                               ('BLOQUEO', 'Consultas bloqueadas; reservas no disponibles.', 'CRITICO')]),
    'autenticacion': dict(nombre='Fallo de autenticación', boton='Simular fallo de autenticación', tipo='AUTENTICACION',
                         titulo='Usuarios sin acceso a la plataforma',
                         descripcion='Múltiples errores de acceso simulados impiden iniciar sesión.',
                         usuarios=280, operaciones=35, impacto=2, urgencia=2, interrumpe=True,
                         eventos=[('ACCESO', 'Primer grupo de accesos rechazados.', 'ADVERTENCIA'),
                                  ('ACCESO', 'Segundo grupo de accesos rechazados.', 'ADVERTENCIA'),
                                  ('ACCESO', 'Tercer grupo de accesos rechazados.', 'ADVERTENCIA')]),
}


def estado_simulacion(componente):
    incidente = bd.session.scalar(bd.select(Incidente).where(
        Incidente.id_componente == componente.id_componente,
        Incidente.estado != 'CERRADO', Incidente.archivado.is_(False))
        .order_by(Incidente.id_incidente.desc()).limit(1))
    respaldo = obtener_respaldo(componente)
    contingencia = bool(respaldo and respaldo.estado == 'RESPALDO_ACTIVO')
    bloqueado = componente.estado != 'OPERATIVO' or contingencia or incidente is not None
    if contingencia:
        mensaje = (f'{componente.nombre} opera mediante contingencia por el incidente activo '
                   f'{incidente.codigo_incidente}. Los escenarios de este componente corresponden al mismo incidente; '
                   'estarán disponibles después del cierre y la normalización.' if incidente else
                   f'{componente.nombre} operando mediante contingencia. Normaliza el componente principal para volver a simular.')
    elif incidente:
        mensaje = (f'{componente.nombre} ya tiene el incidente activo {incidente.codigo_incidente}. '
                   'Los escenarios de este componente corresponden al mismo incidente; estará disponible tras el cierre y la normalización.')
    elif bloqueado:
        mensaje = f'{componente.nombre} en {componente.estado.lower().replace("_", " ")}. Normaliza el entorno antes de volver a simular.'
    else:
        mensaje = ''
    if contingencia and incidente is None:
        incidente = bd.session.scalar(bd.select(Incidente).where(
            Incidente.id_componente == componente.id_componente, Incidente.archivado.is_(False))
            .order_by(Incidente.id_incidente.desc()).limit(1))
    return bloqueado, mensaje, incidente


def prever_escenarios(servicio):
    resultados = {}
    for nombre, escenario in ESCENARIOS.items():
        componente = next(c for c in servicio.componentes if c.tipo == escenario['tipo'])
        eventos = eventos_pendientes(componente)
        advertencias = sum(e.nivel == 'ADVERTENCIA' for e in eventos)
        criticos = sum(e.nivel == 'CRITICO' for e in eventos)
        bloqueo, mensaje, incidente = estado_simulacion(componente)
        if not bloqueo:
            nuevos_criticos = sum(e[2] == 'CRITICO' for e in escenario['eventos'])
            nuevas_advertencias = sum(e[2] == 'ADVERTENCIA' for e in escenario['eventos'])
            genera = criticos + nuevos_criticos >= CRITICOS_NECESARIOS or advertencias + nuevas_advertencias >= ADVERTENCIAS_NECESARIAS
            if nombre == 'latencia':
                mensaje = f'{advertencias}/{ADVERTENCIAS_NECESARIAS} advertencias: ' + (
                    'la próxima ejecución generará un incidente.' if genera else 'se registrará una advertencia, todavía sin incidente.')
            else:
                mensaje = 'La próxima ejecución generará un incidente.' if genera else 'Se registrarán eventos, todavía sin incidente.'
        prioridades = {f'{i}-{u}': calcular_prioridad(max(i, incidente.impacto if incidente else i),
                                                     max(u, incidente.urgencia if incidente else u))
                       for i in range(1, 4) for u in range(1, 4)}
        resultados[nombre] = dict(mensaje=mensaje, bloqueado=bloqueo, prioridades=prioridades,
                                  incidente_id=incidente.id_incidente if incidente else None,
                                  enlace_incidente='Ver incidente activo' if incidente and incidente.estado in ('ABIERTO', 'EN_PROCESO') else 'Ver incidente pendiente de cierre',
                                  prioridad=prioridades[f"{escenario['impacto']}-{escenario['urgencia']}"],
                                  advertencias=advertencias)
    return resultados


def simular_eventos(servicio, nombre, impacto=None, urgencia=None, minutos=5):
    if nombre not in ESCENARIOS:
        raise ValueError('El escenario solicitado no existe.')
    if minutos < 0 or minutos > 120:
        raise ValueError('Los minutos simulados deben estar entre 0 y 120.')
    escenario = ESCENARIOS[nombre]
    impacto = impacto if nombre == 'base_datos' and impacto is not None else escenario['impacto']
    urgencia = urgencia if nombre == 'base_datos' and urgencia is not None else escenario['urgencia']
    if impacto not in (1, 2, 3) or urgencia not in (1, 2, 3):
        raise ValueError('Impacto y urgencia deben estar entre 1 y 3.')
    componente = bd.session.scalar(bd.select(Componente).where(
        Componente.id_servicio == servicio.id_servicio, Componente.tipo == escenario['tipo']))
    bloqueado, mensaje, _ = estado_simulacion(componente)
    if bloqueado:
        raise ValueError(mensaje)
    for tipo, descripcion, nivel in escenario['eventos']:
        bd.session.add(Evento(componente=componente, tipo=tipo, descripcion=descripcion, nivel=nivel, es_simulacion=True))
    bd.session.flush()
    incidente = correlacionar_eventos(componente, escenario, impacto, urgencia, minutos)
    if escenario['interrumpe']:
        componente.estado = 'CAIDO'
    elif componente.estado != 'CAIDO':
        componente.estado = 'ADVERTENCIA'
    actualizar_servicio(servicio)
    registrar_auditoria('SIMULACION_EJECUTADA', 'escenarios', nombre)
    return incidente
