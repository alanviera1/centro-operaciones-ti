import pytest

from conftest import ingresar
from modelos import Evento, bd
from servicios.entorno_academico import restablecer_entorno
from servicios.gestor_incidentes import ejecutar_accion
from servicios.servicio_monitoreado import representar_servicio
from servicios.simulador import prever_escenarios, simular_eventos


def test_prevision_advertencias_y_asociacion(contexto):
    _, servicio = contexto
    restablecer_entorno(servicio)
    assert '0/3' in prever_escenarios(servicio)['latencia']['mensaje']
    componente = next(c for c in servicio.componentes if c.tipo == 'WEB')
    for _ in range(2):
        bd.session.add(Evento(componente=componente, tipo='LATENCIA', descripcion='Latencia de prueba', nivel='ADVERTENCIA'))
    bd.session.flush()
    assert 'generará un incidente' in prever_escenarios(servicio)['latencia']['mensaje']
    incidente = simular_eventos(servicio, 'latencia')
    assert incidente.codigo_incidente in prever_escenarios(servicio)['latencia']['mensaje']
    ejecutar_accion(incidente, 'iniciar')
    ejecutar_accion(incidente, 'reiniciar')
    assert prever_escenarios(servicio)['latencia']['bloqueado']


def test_prevision_prioridad_y_contingencia(contexto):
    _, servicio = contexto
    restablecer_entorno(servicio)
    previsiones = prever_escenarios(servicio)
    assert previsiones['base_datos']['prioridades']['1-1'] == 'BAJA'
    assert previsiones['base_datos']['prioridades']['3-3'] == 'CRITICA'
    incidente = simular_eventos(servicio, 'base_datos', impacto=3, urgencia=3)
    assert prever_escenarios(servicio)['base_datos']['prioridades']['1-1'] == 'CRITICA'
    pagos = simular_eventos(servicio, 'pagos')
    ejecutar_accion(pagos, 'iniciar')
    ejecutar_accion(pagos, 'activar_respaldo')
    assert prever_escenarios(servicio)['pagos']['bloqueado']


@pytest.mark.parametrize('escenario', ['pagos', 'servidor', 'base_datos', 'autenticacion'])
def test_servicio_refleja_falla_y_recuperacion(contexto, escenario):
    _, servicio = contexto
    restablecer_entorno(servicio)
    assert representar_servicio(servicio)['puede_comprar']
    incidente = simular_eventos(servicio, escenario)
    assert not representar_servicio(servicio)['puede_comprar']
    if escenario == 'autenticacion':
        assert not representar_servicio(servicio)['puede_iniciar']
    accion = 'activar_respaldo' if escenario in ('pagos', 'servidor') else 'reiniciar'
    ejecutar_accion(incidente, 'iniciar')
    ejecutar_accion(incidente, accion)
    estado = representar_servicio(servicio)
    assert estado['puede_comprar'] and estado['puede_iniciar']
    assert estado['contingencia'] == (accion == 'activar_respaldo')


def test_servicio_http_valida_estado_y_sesion(contexto):
    aplicacion, servicio = contexto
    restablecer_entorno(servicio)
    cliente = aplicacion.test_client()
    assert cliente.get('/servicio-monitoreado').status_code == 302
    assert cliente.get('/simulador/prevision').status_code == 302
    token = ingresar(cliente, 'OPERADOR')
    datos = {'token_formulario': token, 'accion': 'comprar', 'concierto': 'luz'}
    assert cliente.post('/servicio-monitoreado', data=datos).status_code == 303
    incidente = simular_eventos(servicio, 'pagos')
    bd.session.commit()
    assert cliente.post('/servicio-monitoreado', data=datos).status_code == 409
    assert 'Pagos temporalmente no disponibles' in cliente.get('/servicio-monitoreado').text
    ejecutar_accion(incidente, 'iniciar')
    ejecutar_accion(incidente, 'activar_respaldo')
    bd.session.commit()
    assert cliente.post('/servicio-monitoreado', data=datos).status_code == 303
    assert 'mediante contingencia' in cliente.get('/servicio-monitoreado').text
    assert cliente.post('/servicio-monitoreado').status_code == 400
    assert cliente.get('/simulador/prevision').json['pagos']['bloqueado']
    aplicacion.config['ENTORNO_ACADEMICO'] = False
    assert cliente.get('/simulador/prevision').status_code == 403
