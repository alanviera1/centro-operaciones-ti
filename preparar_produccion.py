import os

from aplicacion import crear_aplicacion
from crear_usuarios import crear_usuarios
from datos_iniciales import cargar_datos
from migrar_bd import migrar_base


def preparar_produccion():
    if not os.getenv('DATABASE_URL'):
        raise ValueError('Configura DATABASE_URL. Este proceso no crea bases locales.')
    aplicacion = crear_aplicacion()
    migrar_base()
    with aplicacion.app_context():
        cargar_datos(incluir_historial=False)
    crear_usuarios(no_interactivo=True)
    print('Esquema, servicio, componentes y usuarios preparados; sin históricos de demostración nuevos.')


if __name__ == '__main__':
    preparar_produccion()
