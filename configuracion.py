import os
from decimal import Decimal
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, make_url

CARPETA = Path(__file__).resolve().parent
load_dotenv(CARPETA / '.env', encoding='utf-8-sig')


def obtener_conexion(nombre=None):
    if os.getenv('DATABASE_URL') and nombre is None:
        conexion = make_url(os.environ['DATABASE_URL'])
        if conexion.get_backend_name() not in ('postgres', 'postgresql'):
            raise ValueError('DATABASE_URL debe apuntar a PostgreSQL.')
        return conexion.set(drivername='postgresql+psycopg')
    return URL.create(
        'postgresql+psycopg',
        username=os.getenv('BD_USUARIO', 'postgres'),
        password=os.getenv('BD_CLAVE', ''),
        host=os.getenv('BD_HOST', 'localhost'),
        port=int(os.getenv('BD_PUERTO', '5432')),
        database=nombre or os.getenv('BD_NOMBRE', 'escudo_ti'),
    )


class Configuracion:
    SQLALCHEMY_DATABASE_URI = obtener_conexion()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'connect_args': {'connect_timeout': 5}, 'pool_pre_ping': True}
    ENTORNO = os.getenv('ENTORNO', 'desarrollo')
    SECRET_KEY = os.getenv('SECRET_KEY') or os.getenv('CLAVE_SESION')
    DEBUG = False
    SESSION_COOKIE_NAME = 'escudo_ti_sesion'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = ENTORNO == 'produccion'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_REFRESH_EACH_REQUEST = False
    ENTORNO_ACADEMICO = os.getenv('ENTORNO_ACADEMICO', 'true').lower() == 'true'
    MAX_CONTENT_LENGTH = 16384
    VALOR_PROMEDIO_ENTRADA = Decimal(os.getenv('VALOR_PROMEDIO_ENTRADA', '130'))
    MINUTOS_PERIODO = int(os.getenv('MINUTOS_PERIODO', '43200'))
