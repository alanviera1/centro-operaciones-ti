import sys
import secrets
from pathlib import Path

import pytest
from flask import g

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aplicacion import crear_aplicacion
from modelos import Servicio, Usuario, bd

CLAVE_PRUEBA = secrets.token_urlsafe(18)


def ingresar(cliente, rol='SUPERVISOR'):
    cliente.get('/login')
    with cliente.session_transaction() as sesion:
        token = sesion['token_formulario']
    respuesta = cliente.post('/login', data={'correo': f'{rol.lower()}@pruebas.local',
        'contrasena': CLAVE_PRUEBA, 'token_formulario': token})
    assert respuesta.status_code == 303
    with cliente.session_transaction() as sesion:
        return sesion['token_formulario']


@pytest.fixture
def contexto():
    aplicacion = crear_aplicacion({'TESTING': True})
    # El contexto exterior de pruebas se comparte; las peticiones reales no.
    def limpiar_usuario_cargado():
        g.pop('_login_user', None)
    aplicacion.before_request_funcs[None].insert(0, limpiar_usuario_cargado)
    with aplicacion.app_context():
        conexion = bd.engine.connect()
        transaccion = conexion.begin()
        motor_original = bd.engines[None]
        bd.engines[None] = conexion
        bd.session.configure(join_transaction_mode='create_savepoint')
        try:
            servicio = bd.session.scalar(bd.select(Servicio).order_by(Servicio.id_servicio).limit(1))
            for rol in ('OPERADOR', 'SUPERVISOR'):
                usuario = Usuario(nombre=f'Prueba {rol}', correo=f'{rol.lower()}@pruebas.local', rol=rol)
                usuario.establecer_contrasena(CLAVE_PRUEBA)
                bd.session.add(usuario)
            bd.session.commit()
            yield aplicacion, servicio
        finally:
            bd.session.remove()
            transaccion.rollback()
            conexion.close()
            bd.engines[None] = motor_original
