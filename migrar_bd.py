from hashlib import sha256
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from configuracion import obtener_conexion
from modelos import Auditoria, Usuario, bd, secuencia_codigo


def migrar_base():
    motor = create_engine(obtener_conexion(), connect_args={'connect_timeout': 5})
    try:
        with motor.begin() as conexion:
            conexion.execute(text('SELECT pg_advisory_xact_lock(17092026)'))
            conexion.execute(text('CREATE TABLE IF NOT EXISTS versiones_esquema '
                                  '(version INTEGER PRIMARY KEY, huella VARCHAR(64) NOT NULL, '
                                  'fecha_hora TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)'))
            for archivo in sorted((Path(__file__).parent / 'migraciones').glob('[0-9]*_*.sql')):
                version = int(archivo.name.split('_')[0])
                contenido = archivo.read_text(encoding='utf-8')
                huella = sha256(contenido.encode()).hexdigest()
                aplicada = conexion.execute(text('SELECT huella FROM versiones_esquema WHERE version = :version'),
                                             {'version': version}).scalar()
                if aplicada:
                    if aplicada != huella:
                        raise ValueError(f'La migración {version:03d} aplicada fue modificada.')
                    continue
                crear_esquema = version == 1 and 'servicios' not in inspect(conexion).get_table_names()
                if crear_esquema:
                    bd.metadata.create_all(conexion)
                else:
                    if version == 1:
                        Usuario.__table__.create(conexion)
                        Auditoria.__table__.create(conexion)
                        secuencia_codigo.create(conexion)
                    for sentencia in contenido.split(';'):
                        if sentencia.strip():
                            conexion.execute(text(sentencia))
                conexion.execute(text('INSERT INTO versiones_esquema (version, huella) VALUES (:version, :huella)'),
                                 {'version': version, 'huella': huella})
                print(f'Migración {version:03d} preparada.')
        print('Esquema actualizado; migraciones confirmadas.')
    finally:
        motor.dispose()


if __name__ == '__main__':
    migrar_base()

