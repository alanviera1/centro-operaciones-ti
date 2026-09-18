import re

import pytest
from flask_login import login_user

from conftest import ingresar
from modelos import Auditoria, Incidente, Usuario, bd
from servicios.entorno_academico import restablecer_entorno
from servicios.gestor_incidentes import acciones_disponibles, ejecutar_accion
from servicios.simulador import prever_escenarios, simular_eventos


def acciones_html(cliente, identificador):
    pagina = cliente.get(f'/incidentes/{identificador}').text
    return re.findall(r'name="accion" value="([^"]+)"', pagina), pagina


def enviar(cliente, identificador, token, accion):
    return cliente.post(f'/incidentes/{identificador}/acciones',
                        data={'token_formulario': token, 'accion': accion})


def test_flujo_por_rol_y_cierre_normaliza_con_auditoria(contexto):
    aplicacion, servicio = contexto
    operador = aplicacion.test_client()
    token_operador = ingresar(operador, 'OPERADOR')
    incidente = simular_eventos(servicio, 'pagos')
    bd.session.commit()

    acciones, pagina = acciones_html(operador, incidente.id_incidente)
    assert acciones == ['iniciar']
    assert 'Detectado' in pagina
    for accion in ('activar_respaldo', 'reiniciar', 'resolver', 'cerrar'):
        assert enviar(operador, incidente.id_incidente, token_operador, accion).status_code in (303, 403)
        assert incidente.estado == 'ABIERTO'

    assert enviar(operador, incidente.id_incidente, token_operador, 'iniciar').status_code == 303
    assert incidente.responsable.rol == 'OPERADOR'
    acciones, _ = acciones_html(operador, incidente.id_incidente)
    assert acciones == ['activar_respaldo', 'reiniciar', 'escalar']

    assert enviar(operador, incidente.id_incidente, token_operador, 'escalar').status_code == 303
    assert incidente.estado == 'EN_PROCESO' and incidente.fecha_recuperacion is None
    assert 'escalar' not in acciones_html(operador, incidente.id_incidente)[0]
    assert enviar(operador, incidente.id_incidente, token_operador, 'escalar').status_code == 303
    assert sum(a.accion == 'Escalar incidente' for a in incidente.acciones) == 1

    assert enviar(operador, incidente.id_incidente, token_operador, 'activar_respaldo').status_code == 303
    assert incidente.fecha_recuperacion is not None
    assert 'Servicio recuperado' in acciones_html(operador, incidente.id_incidente)[1]
    assert acciones_html(operador, incidente.id_incidente)[0] == ['resolver']
    assert enviar(operador, incidente.id_incidente, token_operador, 'cerrar').status_code == 403
    assert enviar(operador, incidente.id_incidente, token_operador, 'resolver').status_code == 303
    acciones, pagina = acciones_html(operador, incidente.id_incidente)
    assert acciones == []
    assert 'Incidente resuelto. Pendiente de validación y cierre por supervisor.' in pagina
    assert enviar(operador, incidente.id_incidente, token_operador, 'cerrar').status_code == 403
    assert incidente.fecha_cierre is None

    supervisor = aplicacion.test_client()
    token_supervisor = ingresar(supervisor)
    assert acciones_html(supervisor, incidente.id_incidente)[0] == ['cerrar']
    assert 'Cerrar y normalizar servicio' in acciones_html(supervisor, incidente.id_incidente)[1]
    assert enviar(supervisor, incidente.id_incidente, token_supervisor, 'cerrar').status_code == 303
    assert incidente.estado == 'CERRADO'
    assert incidente.fecha_cierre >= incidente.fecha_resolucion
    assert incidente.componente.estado == 'OPERATIVO'
    assert next(c for c in servicio.componentes if c.tipo == 'PAGOS_ALTERNATIVA').estado == 'OPERATIVO'
    nombres = [a.accion for a in incidente.acciones]
    assert nombres.count('Escalar incidente') == 1
    assert 'Restaurar componente principal' in nombres
    assert 'Desactivar contingencia' in nombres
    assert nombres[-1] == 'Cerrar y normalizar servicio'
    for nombre in ('Escalar incidente', 'Restaurar componente principal', 'Desactivar contingencia',
                   'Cerrar y normalizar servicio'):
        assert bd.session.scalar(bd.select(Auditoria).where(
            Auditoria.referencia == incidente.codigo_incidente, Auditoria.accion == nombre))


@pytest.mark.parametrize('escenario,etiqueta', [
    ('servidor', 'Reiniciar servidor web'),
    ('pagos', 'Reintentar pasarela principal'),
    ('base_datos', 'Restablecer servicio de base de datos'),
    ('autenticacion', 'Reiniciar servicio de autenticación'),
])
def test_acciones_tecnicas_corresponden_al_componente(contexto, escenario, etiqueta):
    _, servicio = contexto
    restablecer_entorno(servicio)
    incidente = simular_eventos(servicio, escenario)
    assert acciones_disponibles(incidente) == [('iniciar', 'Iniciar atención')]
    ejecutar_accion(incidente, 'iniciar')
    nombres = [nombre for _, nombre in acciones_disponibles(incidente)]
    assert etiqueta in nombres
    assert 'Escalar incidente' not in nombres
    assert ('Activar servidor de respaldo' in nombres) == (escenario == 'servidor')
    assert ('Activar pasarela alternativa' in nombres) == (escenario == 'pagos')


def test_dos_escenarios_mismo_componente_apuntan_al_mismo_incidente(contexto):
    _, servicio = contexto
    restablecer_entorno(servicio)
    incidente = simular_eventos(servicio, 'servidor')
    previsiones = prever_escenarios(servicio)
    assert previsiones['servidor']['incidente_id'] == incidente.id_incidente
    assert previsiones['latencia']['incidente_id'] == incidente.id_incidente
    assert 'mismo incidente' in previsiones['latencia']['mensaje']
    with pytest.raises(ValueError, match='incidente activo'):
        simular_eventos(servicio, 'latencia')
    assert bd.session.scalar(bd.select(bd.func.count()).select_from(Incidente).where(
        Incidente.id_componente == incidente.id_componente, Incidente.estado != 'CERRADO')) == 1


def test_supervisor_tambien_puede_atender_y_resolver(contexto):
    aplicacion, servicio = contexto
    supervisor = aplicacion.test_client()
    token = ingresar(supervisor)
    incidente = simular_eventos(servicio, 'autenticacion')
    assert enviar(supervisor, incidente.id_incidente, token, 'iniciar').status_code == 303
    assert 'escalar' not in acciones_html(supervisor, incidente.id_incidente)[0]
    assert enviar(supervisor, incidente.id_incidente, token, 'escalar').status_code == 403
    with aplicacion.test_request_context('/'):
        login_user(bd.session.scalar(bd.select(Usuario).where(Usuario.correo == 'supervisor@pruebas.local')))
        with pytest.raises(PermissionError, match='operador'):
            ejecutar_accion(incidente, 'escalar')
    assert incidente.estado == 'EN_PROCESO' and incidente.fecha_recuperacion is None
    for accion in ('reiniciar', 'resolver'):
        assert enviar(supervisor, incidente.id_incidente, token, accion).status_code == 303
    assert incidente.responsable.rol == 'SUPERVISOR'
    assert incidente.estado == 'RESUELTO'
