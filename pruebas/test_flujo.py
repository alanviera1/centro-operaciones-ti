from datetime import timedelta
from decimal import Decimal

import pytest
from conftest import ingresar
from flask_login import login_user

from modelos import Evento, Incidente, Usuario, ahora, bd
from servicios.gestor_disponibilidad import calcular_disponibilidad, medir_servicio, unir_intervalos
from servicios.gestor_incidentes import calcular_prioridad, ejecutar_accion
from servicios.simulador import simular_eventos


def test_matriz_completa_y_valores_invalidos():
    esperadas = [['BAJA', 'BAJA', 'MEDIA'], ['BAJA', 'MEDIA', 'ALTA'], ['MEDIA', 'ALTA', 'CRITICA']]
    for impacto in range(1, 4):
        for urgencia in range(1, 4):
            assert calcular_prioridad(impacto, urgencia) == esperadas[impacto - 1][urgencia - 1]
    with pytest.raises(ValueError):
        calcular_prioridad(0, 3)


def test_disponibilidad_e_intervalos_superpuestos():
    assert calcular_disponibilidad(1000, 10) == 99
    assert calcular_disponibilidad(100, 150) == 0
    with pytest.raises(ValueError):
        calcular_disponibilidad(0, 1)
    inicio = ahora()
    intervalos = [(inicio, inicio + timedelta(minutes=10)),
                  (inicio + timedelta(minutes=5), inicio + timedelta(minutes=15))]
    assert unir_intervalos(intervalos) == 15


def test_pagos_critico_persistencia_y_correlacion(contexto):
    _, servicio = contexto
    incidente = simular_eventos(servicio, 'pagos')
    bd.session.commit()
    identificador = incidente.id_incidente
    bd.session.expire_all()
    guardado = bd.session.get(Incidente, identificador)
    assert guardado.prioridad == 'CRITICA'
    assert guardado.perdida_estimada == Decimal('24180.00')
    assert guardado.usuarios_afectados == 742
    assert len(guardado.eventos) == 3
    with pytest.raises(ValueError, match='incidente activo'):
        simular_eventos(servicio, 'pagos')
    assert bd.session.scalar(bd.select(bd.func.count()).select_from(Incidente).where(
        Incidente.id_componente == guardado.id_componente, Incidente.estado != 'CERRADO')) == 1
    assert bd.session.connection().execute(bd.select(Incidente.perdida_estimada).where(
        Incidente.id_incidente == identificador)).scalar() == Decimal('24180.00')


def test_recuperacion_resolucion_cierre_y_retorno(contexto):
    aplicacion, servicio = contexto
    incidente = simular_eventos(servicio, 'pagos', minutos=5)
    bd.session.flush()
    with pytest.raises(PermissionError):
        ejecutar_accion(incidente, 'cerrar')
    with pytest.raises(ValueError):
        ejecutar_accion(incidente, 'resolver')
    ejecutar_accion(incidente, 'iniciar')
    ejecutar_accion(incidente, 'activar_respaldo')
    assert servicio.estado == 'OPERATIVO_CON_RESPALDO'
    assert incidente.componente.estado == 'CAIDO'
    assert incidente.interrupciones[0].fecha_fin is not None
    assert float(incidente.interrupciones[0].minutos_caida) >= 5
    assert medir_servicio(servicio)['usuarios'] == 0
    ejecutar_accion(incidente, 'resolver')
    with aplicacion.test_request_context('/'):
        login_user(bd.session.scalar(bd.select(Usuario).where(Usuario.rol == 'SUPERVISOR').order_by(Usuario.id_usuario.desc())))
        ejecutar_accion(incidente, 'cerrar')
    assert incidente.fecha_cierre >= incidente.fecha_resolucion >= incidente.fecha_recuperacion
    with pytest.raises(PermissionError):
        ejecutar_accion(incidente, 'cerrar')
    with pytest.raises(ValueError):
        ejecutar_accion(incidente, 'restaurar_principal')
    assert incidente.componente.estado == 'OPERATIVO'
    assert next(c for c in servicio.componentes if c.tipo == 'PAGOS_ALTERNATIVA').estado == 'OPERATIVO'
    bd.session.commit()
    assert len(incidente.acciones) >= 5


def test_latencia_agrupada_que_empeora_a_caida(contexto):
    _, servicio = contexto
    from servicios.entorno_academico import restablecer_entorno
    from modelos import Evento
    restablecer_entorno(servicio)
    componente = next(c for c in servicio.componentes if c.tipo == 'WEB')
    for _ in range(2):
        bd.session.add(Evento(componente=componente, tipo='LATENCIA', descripcion='Latencia elevada', nivel='ADVERTENCIA'))
    bd.session.flush()
    incidente = simular_eventos(servicio, 'latencia')
    assert incidente.prioridad == 'BAJA'
    assert len(incidente.interrupciones) == 0
    with pytest.raises(ValueError, match='incidente activo'):
        simular_eventos(servicio, 'servidor')
    assert incidente.estado == 'ABIERTO'


def test_fallas_simultaneas_y_prioridad_configurable(contexto):
    _, servicio = contexto
    from servicios.entorno_academico import restablecer_entorno
    restablecer_entorno(servicio)
    pagos = simular_eventos(servicio, 'pagos')
    servidor = simular_eventos(servicio, 'servidor')
    base = simular_eventos(servicio, 'base_datos', impacto=1, urgencia=1)
    acceso = simular_eventos(servicio, 'autenticacion')
    assert base.prioridad == 'BAJA'
    assert acceso.prioridad == 'MEDIA'
    ejecutar_accion(pagos, 'iniciar')
    ejecutar_accion(pagos, 'activar_respaldo')
    assert servicio.estado == 'CAIDO'
    ejecutar_accion(servidor, 'iniciar')
    ejecutar_accion(servidor, 'activar_respaldo')
    ejecutar_accion(base, 'iniciar')
    ejecutar_accion(base, 'reiniciar')
    ejecutar_accion(acceso, 'iniciar')
    ejecutar_accion(acceso, 'reiniciar')
    assert servicio.estado == 'OPERATIVO_CON_RESPALDO'


def test_error_revierte_toda_la_simulacion(contexto, monkeypatch):
    _, servicio = contexto
    cantidad = bd.session.scalar(bd.select(bd.func.count(Evento.id_evento)))
    def fallar(*argumentos):
        raise RuntimeError('Falla de prueba antes de crear el incidente')
    monkeypatch.setattr('servicios.simulador.correlacionar_eventos', fallar)
    with pytest.raises(RuntimeError):
        with bd.session.begin_nested():
            simular_eventos(servicio, 'pagos')
    assert bd.session.scalar(bd.select(bd.func.count(Evento.id_evento))) == cantidad


def test_rutas_validacion_y_formularios(contexto):
    aplicacion, servicio = contexto
    cliente = aplicacion.test_client()
    ingresar(cliente)
    for ruta in ['/', '/incidentes', '/historial', '/eventos']:
        assert cliente.get(ruta).status_code == 200
    assert cliente.get('/incidentes/99999999').status_code == 404
    assert cliente.post('/simulaciones/pagos').status_code == 400
    with cliente.session_transaction() as sesion:
        token = sesion['token_formulario']
    respuesta = cliente.post('/simulaciones/pagos', data={'token_formulario': token, 'minutos': '-1'}, follow_redirects=True)
    assert 'entre 0 y 120' in respuesta.text
    respuesta = cliente.post('/simulaciones/pagos', data={'token_formulario': token}, follow_redirects=True)
    assert 'Crítica' in respuesta.text
    incidente = bd.session.scalar(bd.select(Incidente).where(Incidente.estado == 'ABIERTO'))
    for accion in ['iniciar', 'activar_respaldo', 'resolver', 'cerrar']:
        respuesta = cliente.post(f'/incidentes/{incidente.id_incidente}/acciones',
                                 data={'token_formulario': token, 'accion': accion}, follow_redirects=True)
        assert respuesta.status_code == 200
        assert 'class="toast exito"' in respuesta.text
