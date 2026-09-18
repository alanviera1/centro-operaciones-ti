from datetime import timedelta
from decimal import Decimal

from modelos import AccionIncidente, Componente, Evento, Incidente, Interrupcion, Servicio, ahora, bd


def cargar_datos(incluir_historial=True):
    if bd.session.scalar(bd.select(Servicio).limit(1)):
        return
    servicio = Servicio(nombre='Venta de entradas online',
                        descripcion='Plataforma de venta de entradas para conciertos de alta demanda.',
                        sla_objetivo=Decimal('99.90'))
    bd.session.add(servicio)
    componentes = {}
    for tipo, nombre in [('WEB', 'Servidor web principal'), ('WEB_RESPALDO', 'Servidor web de respaldo'),
                         ('BD', 'Base de datos'), ('PAGOS', 'Pasarela de pagos principal'),
                         ('PAGOS_ALTERNATIVA', 'Pasarela de pagos alternativa'),
                         ('AUTENTICACION', 'Servicio de autenticación')]:
        componente = Componente(servicio=servicio, nombre=nombre, tipo=tipo)
        componentes[tipo] = componente
        bd.session.add(componente)
    bd.session.flush()
    if not incluir_historial:
        bd.session.commit()
        return
    for tipo, dias, duracion, titulo, prioridad, impacto, urgencia in [
        ('BD', 3, 7, 'Consultas bloqueadas en reservas', 'ALTA', 2, 3),
        ('AUTENTICACION', 1, 4, 'Interrupción del acceso de usuarios', 'MEDIA', 2, 2),
    ]:
        inicio = ahora() - timedelta(days=dias)
        recuperacion = inicio + timedelta(minutes=duracion)
        incidente = Incidente(
            id_servicio=servicio.id_servicio, componente=componentes[tipo], titulo=titulo,
            descripcion='Registro histórico de demostración académica. No corresponde a una empresa real.',
            impacto=impacto, urgencia=urgencia, prioridad=prioridad, estado='CERRADO',
            usuarios_afectados=80, operaciones_fallidas=10, perdida_estimada=Decimal('1300'),
            fecha_inicio=inicio, fecha_recuperacion=recuperacion,
            fecha_resolucion=recuperacion + timedelta(minutes=1),
            fecha_cierre=recuperacion + timedelta(minutes=2), demostracion=True, es_simulacion=True,
        )
        bd.session.add(incidente)
        bd.session.add(Interrupcion(id_servicio=servicio.id_servicio, incidente=incidente,
                                   fecha_inicio=inicio, fecha_fin=recuperacion, minutos_caida=duracion))
        bd.session.add(Evento(componente=componentes[tipo], incidente=incidente, tipo='DEMO_HISTORICA',
                             descripcion='Falla de demostración detectada y atendida.', nivel='CRITICO', es_simulacion=True,
                             fecha_hora=inicio, atendido=True))
        for accion, fecha in [('Incidente generado', inicio), ('Reiniciar componente', recuperacion),
                              ('Marcar como resuelto', incidente.fecha_resolucion),
                              ('Cerrar incidente', incidente.fecha_cierre)]:
            bd.session.add(AccionIncidente(incidente=incidente, accion=accion,
                                          resultado='Dato histórico de demostración académica.', fecha_hora=fecha))
    bd.session.add(Evento(componente=componentes['WEB'], tipo='INICIO',
                         descripcion='Monitoreo académico iniciado. Todos los componentes operativos.',
                         nivel='INFORMATIVO', atendido=True, es_simulacion=True))
    bd.session.commit()
