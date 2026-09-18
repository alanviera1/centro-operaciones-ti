import secrets

from sqlalchemy import text

from aplicacion import crear_aplicacion
from datos_iniciales import cargar_datos
from modelos import Componente, Incidente, Servicio, Usuario, bd


def test_esquema_nuevo_sin_historicos_y_semilla_idempotente():
    aplicacion = crear_aplicacion({'TESTING': True})
    with aplicacion.app_context():
        conexion = bd.engine.connect()
        transaccion = conexion.begin()
        motor_original = bd.engines[None]
        esquema = 'prueba_' + secrets.token_hex(6)
        try:
            conexion.execute(text(f'CREATE SCHEMA {esquema}'))
            conexion.execute(text(f'SET LOCAL search_path TO {esquema}'))
            bd.metadata.create_all(conexion)
            bd.engines[None] = conexion
            bd.session.configure(join_transaction_mode='create_savepoint')
            cargar_datos(incluir_historial=False)
            cargar_datos(incluir_historial=False)
            assert bd.session.scalar(bd.select(bd.func.count()).select_from(Servicio)) == 1
            assert bd.session.scalar(bd.select(bd.func.count()).select_from(Componente)) == 6
            assert bd.session.scalar(bd.select(bd.func.count()).select_from(Incidente)) == 0
            usuario = Usuario(nombre='Inicial', correo='inicial@pruebas.local', rol='SUPERVISOR')
            usuario.establecer_contrasena(secrets.token_urlsafe(20))
            bd.session.add(usuario)
            bd.session.commit()
            assert usuario.id_usuario is not None
        finally:
            bd.session.remove()
            transaccion.rollback()
            conexion.close()
            bd.engines[None] = motor_original
