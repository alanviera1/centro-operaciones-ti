import os

from waitress import serve

from aplicacion import crear_aplicacion


def iniciar_servidor():
    aplicacion = crear_aplicacion()
    host = os.getenv('HOST', '0.0.0.0' if aplicacion.config['ENTORNO'] == 'produccion' else '127.0.0.1')
    puerto = int(os.getenv('PORT') or os.getenv('PUERTO', '5055'))
    aplicacion.logger.info('Centro de Operaciones TI: servidor WSGI iniciado, entorno %s, puerto %s.',
                           aplicacion.config['ENTORNO'], puerto)
    serve(aplicacion, host=host, port=puerto, threads=4)


if __name__ == '__main__':
    iniciar_servidor()
