from sqlalchemy import create_engine, text

from configuracion import obtener_conexion


def preparar_base():
    conexion = obtener_conexion()
    if conexion.database != 'escudo_ti':
        raise ValueError('Este instalador solamente puede crear escudo_ti.')
    motor = create_engine(obtener_conexion('postgres'), isolation_level='AUTOCOMMIT',
                          connect_args={'connect_timeout': 5})
    with motor.connect() as sesion:
        existe = sesion.execute(text('SELECT 1 FROM pg_database WHERE datname = :nombre'),
                                {'nombre': 'escudo_ti'}).scalar()
        if not existe:
            sesion.execute(text('CREATE DATABASE escudo_ti'))
            print('Base escudo_ti creada. No se modificaron otras bases.')
        else:
            print('La base escudo_ti ya existe; no se elimina ni se reemplaza.')
    motor.dispose()
    from migrar_bd import migrar_base
    migrar_base()
    from aplicacion import crear_aplicacion
    from datos_iniciales import cargar_datos
    from modelos import bd
    aplicacion = crear_aplicacion()
    with aplicacion.app_context():
        bd.create_all()
        cargar_datos()
    print('Tablas y datos iniciales listos.')


if __name__ == '__main__':
    preparar_base()
