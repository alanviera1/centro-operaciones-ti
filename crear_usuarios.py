import os
from getpass import getpass

from aplicacion import crear_aplicacion
from modelos import Usuario, bd
from servicios.auditoria import registrar_auditoria


def crear_usuarios(no_interactivo=False, actualizar_existentes=False):
    aplicacion = crear_aplicacion()
    with aplicacion.app_context():
        for rol, correo, nombre in [('OPERADOR', 'operador@escudoti.local', 'Alan'),
                                     ('SUPERVISOR', 'supervisor@escudoti.local', 'Supervisor TI')]:
            usuario = bd.session.scalar(bd.select(Usuario).where(Usuario.correo == correo))
            if usuario and not actualizar_existentes:
                print(f'{correo}: ya existe; no se cambia su contraseña.')
                continue
            contrasena = os.getenv(f'CLAVE_INICIAL_{rol}')
            if not contrasena and no_interactivo:
                raise ValueError(f'Configura CLAVE_INICIAL_{rol} para crear la cuenta inicial.')
            contrasena = contrasena or getpass(f'Contraseña inicial de {correo}: ')
            if usuario:
                usuario.establecer_contrasena(contrasena)
                registrar_auditoria('CREDENCIAL_ACTUALIZADA', 'usuarios', correo)
                continue
            usuario = Usuario(nombre=nombre, correo=correo, rol=rol)
            usuario.establecer_contrasena(contrasena)
            bd.session.add(usuario)
            bd.session.flush()
            registrar_auditoria('USUARIO_CREADO', 'usuarios', correo)
        bd.session.commit()
    print('Usuarios iniciales listos. No hay registro público.')


if __name__ == '__main__':
    crear_usuarios()
