from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from conftest import CLAVE_PRUEBA, ingresar
from modelos import AccionIncidente, ArchivoAcademico, Auditoria, Evento, Incidente, Usuario, ahora, bd
from servicios.entorno_academico import restablecer_entorno
from servicios.gestor_disponibilidad import medir_servicio
from servicios.gestor_incidentes import ejecutar_accion
from servicios.simulador import simular_eventos


def enviar(cliente, ruta, token, **datos):
    return cliente.post(ruta, data={'token_formulario': token, **datos})


def test_login_correcto_y_hash(contexto):
    aplicacion, _ = contexto
    cliente = aplicacion.test_client()
    ingresar(cliente, 'OPERADOR')
    assert cliente.get('/').status_code == 200
    usuario = bd.session.scalar(bd.select(Usuario).where(Usuario.correo == 'operador@pruebas.local'))
    assert usuario.contrasena_hash.startswith('scrypt:')
    assert usuario.contrasena_hash != CLAVE_PRUEBA
    assert usuario.verificar_contrasena(CLAVE_PRUEBA)
    assert bd.session.scalar(bd.select(Auditoria).where(
        Auditoria.accion == 'SESION_INICIADA', Auditoria.id_usuario == usuario.id_usuario))


def test_login_incorrecto_y_bloqueo(contexto):
    aplicacion, _ = contexto
    cliente = aplicacion.test_client()
    cliente.get('/login')
    with cliente.session_transaction() as sesion:
        token = sesion['token_formulario']
    for intento in range(5):
        respuesta = enviar(cliente, '/login', token, correo='operador@pruebas.local', contrasena='invalida')
        assert respuesta.status_code == 401
    assert enviar(cliente, '/login', token, correo='operador@pruebas.local', contrasena=CLAVE_PRUEBA).status_code == 401
    usuario = bd.session.scalar(bd.select(Usuario).where(Usuario.correo == 'operador@pruebas.local'))
    assert usuario.bloqueado_hasta > ahora()
    usuario.bloqueado_hasta = ahora() - timedelta(seconds=1)
    bd.session.commit()
    assert enviar(cliente, '/login', token, correo='operador@pruebas.local', contrasena=CLAVE_PRUEBA).status_code == 303


@pytest.mark.parametrize('ruta', ['/', '/incidentes', '/eventos', '/historial', '/simulador', '/auditoria', '/incidentes/1'])
def test_rutas_protegidas(contexto, ruta):
    aplicacion, _ = contexto
    respuesta = aplicacion.test_client().get(ruta)
    assert respuesta.status_code == 302
    assert respuesta.location.endswith('/login')


def test_operador_resuelve_supervisor_cierra_y_audita(contexto):
    aplicacion, servicio = contexto
    operador = aplicacion.test_client()
    token = ingresar(operador, 'OPERADOR')
    respuesta = enviar(operador, '/simulaciones/pagos', token)
    assert respuesta.status_code == 303
    incidente = bd.session.scalar(bd.select(Incidente).where(Incidente.estado == 'ABIERTO'))
    ruta = f'/incidentes/{incidente.id_incidente}/acciones'
    for accion in ['iniciar', 'activar_respaldo', 'resolver']:
        assert enviar(operador, ruta, token, accion=accion).status_code == 303
    assert enviar(operador, ruta, token, accion='cerrar').status_code == 403
    assert incidente.estado == 'RESUELTO'
    assert incidente.fecha_cierre is None
    assert 'Pendiente de validación y cierre por supervisor' in operador.get(f'/incidentes/{incidente.id_incidente}').text
    supervisor = aplicacion.test_client()
    token_supervisor = ingresar(supervisor)
    assert enviar(supervisor, ruta, token_supervisor, accion='cerrar').status_code == 303
    assert incidente.estado == 'CERRADO'
    assert incidente.responsable.rol == 'OPERADOR'
    ultima = bd.session.scalar(bd.select(AccionIncidente).where(AccionIncidente.id_incidente == incidente.id_incidente)
                                .order_by(AccionIncidente.id_accion.desc()))
    assert ultima.usuario.rol == 'SUPERVISOR'
    assert ultima.accion == 'Cerrar y normalizar servicio'
    assert incidente.componente.estado == 'OPERATIVO'


def test_permisos_reset_auditoria_y_confirmacion(contexto):
    aplicacion, _ = contexto
    cliente = aplicacion.test_client()
    token = ingresar(cliente, 'OPERADOR')
    assert enviar(cliente, '/entorno/restablecer', token, confirmacion='RESTABLECER').status_code == 403
    assert cliente.get('/auditoria').status_code == 403
    supervisor = aplicacion.test_client()
    token = ingresar(supervisor)
    assert enviar(supervisor, '/entorno/restablecer', token).status_code == 400
    assert supervisor.get('/auditoria').status_code == 200


def test_reset_preserva_evidencia_usuarios_y_metricas(contexto):
    aplicacion, servicio = contexto
    incidente = simular_eventos(servicio, 'pagos')
    bd.session.commit()
    codigo = incidente.codigo_incidente
    cantidad = bd.session.scalar(bd.select(bd.func.count()).select_from(Incidente))
    usuarios = bd.session.scalar(bd.select(bd.func.count()).select_from(Usuario))
    cliente = aplicacion.test_client()
    token = ingresar(cliente)
    assert enviar(cliente, '/entorno/restablecer', token, confirmacion='RESTABLECER').status_code == 303
    assert bd.session.scalar(bd.select(bd.func.count()).select_from(Incidente)) == 0
    assert bd.session.scalar(bd.select(bd.func.count()).select_from(Usuario)) == usuarios
    metricas = medir_servicio(servicio)
    assert metricas['disponibilidad'] == 100
    assert metricas['caida'] == 0
    assert servicio.estado == 'OPERATIVO'
    assert codigo not in cliente.get('/historial').text
    assert codigo in cliente.get('/historial?archivados=1').text
    assert bd.session.scalar(bd.select(Auditoria).where(Auditoria.accion == 'ENTORNO_RESTABLECIDO'))
    historial = cliente.get('/historial').text
    assert historial.count('Ciclos anteriores →') == 1
    assert 'Ver archivo por ciclos' not in historial
    assert '/archivo-academico' not in cliente.get('/auditoria').text
    assert '/archivo-academico' not in cliente.get('/eventos').text
    archivo = bd.session.scalar(bd.select(ArchivoAcademico).order_by(ArchivoAcademico.id_archivo.desc()))
    listado = cliente.get('/archivo-academico').text
    assert f'Ciclo {archivo.id_archivo}' in listado
    forma = 'incidente' if cantidad == 1 else 'incidentes'
    assert f'>{cantidad}</strong><span>{forma}</span>' in listado
    assert codigo in listado
    assert 'Ver evidencia del ciclo →' in listado
    assert 'Archivo académico' not in listado and 'archivo por ciclos' not in listado
    detalle = cliente.get(f'/archivo-academico/{archivo.id_archivo}').text
    assert codigo in detalle
    assert 'Línea de tiempo' in detalle and 'Eventos del ciclo' in detalle
    assert 'Auditoría del ciclo' in detalle
    assert ('Fin del ciclo de demostración. Los estados y tiempos se conservan tal como estaban '
            'al restablecer el entorno. Los incidentes pendientes conservan su estado original.') in detalle
    assert 'ciclo académico' not in detalle and 'restablecimiento académico' not in detalle
    contenido = archivo.contenido
    for cantidad_muestra, singular in ((1, True), (2, False)):
        archivo.contenido = {**contenido,
            'incidentes': contenido['incidentes'][:1] * cantidad_muestra,
            'eventos': contenido['eventos'][:1] * cantidad_muestra,
            'acciones_incidente': contenido['acciones_incidente'][:1] * cantidad_muestra}
        bd.session.flush()
        etiqueta = ('incidente', 'evento', 'acción') if singular else ('incidentes', 'eventos', 'acciones')
        for ruta in ('/archivo-academico', f'/archivo-academico/{archivo.id_archivo}'):
            pagina = cliente.get(ruta).text
            for palabra in etiqueta:
                assert f'<strong>{cantidad_muestra}</strong><span>{palabra}</span>' in pagina


def test_reset_no_toca_incidente_externo(contexto):
    _, servicio = contexto
    incidente = simular_eventos(servicio, 'base_datos')
    incidente.es_simulacion = False
    bd.session.flush()
    with pytest.raises(ValueError):
        restablecer_entorno(servicio)
    assert not incidente.archivado
    assert incidente.estado == 'ABIERTO'


def test_codigo_independiente_unico_y_fk(contexto):
    _, servicio = contexto
    primero = simular_eventos(servicio, 'pagos')
    segundo = simular_eventos(servicio, 'base_datos')
    assert primero.codigo_incidente != segundo.codigo_incidente
    assert primero.codigo_incidente.startswith(f'INC-{ahora().year}-')
    original = primero.codigo_incidente
    with pytest.raises(IntegrityError):
        with bd.session.begin_nested():
            segundo.codigo_incidente = original
            bd.session.flush()
    with pytest.raises(IntegrityError):
        with bd.session.begin_nested():
            bd.session.add(AccionIncidente(id_incidente=primero.id_incidente, id_usuario=99999999,
                                           accion='Inválida', resultado='Prueba de FK'))
            bd.session.flush()


def test_filtros_paginacion_y_vistas_separadas(contexto):
    aplicacion, servicio = contexto
    incidente = simular_eventos(servicio, 'pagos')
    bd.session.commit()
    cliente = aplicacion.test_client()
    ingresar(cliente)
    assert incidente.codigo_incidente in cliente.get('/incidentes?prioridad=CRITICA').text
    assert incidente.codigo_incidente not in cliente.get('/incidentes?prioridad=BAJA').text
    assert incidente.codigo_incidente in cliente.get('/incidentes?codigo=' + incidente.codigo_incidente).text
    assert incidente.codigo_incidente not in cliente.get('/historial').text
    assert incidente.codigo_incidente not in cliente.get('/incidentes?pagina=999').text
    assert '/simulaciones/pagos' not in cliente.get('/').text
    assert '/simulaciones/pagos' in cliente.get('/simulador').text
    assert 'DEMO PRINCIPAL' not in cliente.get('/simulador').text
    assert cliente.get('/eventos?fecha=no-valida').status_code == 400
    assert '186 transacciones rechazadas' not in cliente.get('/eventos?nivel=INFORMATIVO').text


def test_sesion_cerrada_csrf_y_usuario_inactivo(contexto):
    aplicacion, _ = contexto
    cliente = aplicacion.test_client()
    token = ingresar(cliente)
    assert cliente.post('/simulaciones/pagos').status_code == 400
    assert enviar(cliente, '/salir', token).status_code == 303
    assert cliente.get('/').status_code == 302
    ingresar(cliente, 'OPERADOR')
    usuario = bd.session.scalar(bd.select(Usuario).where(Usuario.correo == 'operador@pruebas.local'))
    usuario.activo = False
    bd.session.commit()
    assert cliente.get('/').status_code == 302


def test_sla_cumplido_con_riesgo_y_incumplido(contexto):
    _, servicio = contexto
    restablecer_entorno(servicio)
    simular_eventos(servicio, 'pagos', minutos=36)
    metricas = medir_servicio(servicio)
    assert metricas['estado_sla'] == 'CUMPLIDO' and metricas['en_riesgo']
    restablecer_entorno(servicio)
    simular_eventos(servicio, 'pagos', minutos=60)
    metricas = medir_servicio(servicio)
    assert metricas['estado_sla'] == 'INCUMPLIDO'
    assert metricas['restante'] == 0


def test_cabeceras_y_laboratorio_desactivado(contexto):
    aplicacion, _ = contexto
    cliente = aplicacion.test_client()
    token = ingresar(cliente)
    aplicacion.config['ENTORNO_ACADEMICO'] = False
    assert cliente.get('/simulador').status_code == 403
    assert enviar(cliente, '/simulaciones/pagos', token).status_code == 403
    assert enviar(cliente, '/entorno/restablecer', token, confirmacion='RESTABLECER').status_code == 403
    respuesta = cliente.get('/')
    assert respuesta.headers['X-Frame-Options'] == 'DENY'
    assert respuesta.headers['Cache-Control'] == 'no-store'
    assert "script-src 'self'" in respuesta.headers['Content-Security-Policy']


def test_produccion_exige_secreto_y_cookie_segura():
    from aplicacion import crear_aplicacion
    import secrets
    with pytest.raises(ValueError, match='32 caracteres'):
        crear_aplicacion({'ENTORNO': 'produccion', 'SECRET_KEY': 'corta'})
    aplicacion = crear_aplicacion({'ENTORNO': 'produccion', 'SECRET_KEY': secrets.token_urlsafe(32),
                                  'DEBUG': True, 'SESSION_COOKIE_SECURE': False})
    respuesta = aplicacion.test_client().get('/login', base_url='https://escudo.example')
    cookie = next(valor for valor in respuesta.headers.getlist('Set-Cookie')
                  if valor.startswith(aplicacion.config['SESSION_COOKIE_NAME'] + '='))
    assert all(atributo in cookie for atributo in ('Secure', 'HttpOnly', 'SameSite=Lax'))
    assert respuesta.headers['Strict-Transport-Security'] == 'max-age=31536000'
    assert not aplicacion.debug


def test_paginacion_real_conserva_filtros(contexto):
    aplicacion, servicio = contexto
    from flask_login import login_user
    codigos = []
    for _ in range(14):
        incidente = simular_eventos(servicio, 'base_datos')
        ejecutar_accion(incidente, 'iniciar')
        ejecutar_accion(incidente, 'reiniciar')
        ejecutar_accion(incidente, 'resolver')
        with aplicacion.test_request_context('/'):
            login_user(bd.session.scalar(bd.select(Usuario).where(Usuario.correo == 'supervisor@pruebas.local')))
            ejecutar_accion(incidente, 'cerrar')
        codigos.append(incidente.codigo_incidente)
    bd.session.commit()
    cliente = aplicacion.test_client()
    ingresar(cliente)
    ruta = f'/historial?prioridad=ALTA&componente={incidente.id_componente}'
    primera = cliente.get(ruta).text
    segunda = cliente.get(ruta + '&pagina=2').text
    assert 'pagina=2' in primera
    assert f'componente={incidente.id_componente}' in primera and 'prioridad=ALTA' in primera
    assert sum(codigo in primera for codigo in codigos) == 12
    assert sum(codigo in segunda for codigo in codigos) == 2


def test_conexion_remota_solo_postgresql(monkeypatch):
    from configuracion import obtener_conexion
    monkeypatch.setenv('DATABASE_URL', 'postgres://usuario:clave@servidor/base?sslmode=require')
    conexion = obtener_conexion()
    assert conexion.drivername == 'postgresql+psycopg'
    assert conexion.query['sslmode'] == 'require'
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///otra.db')
    with pytest.raises(ValueError, match='PostgreSQL'):
        obtener_conexion()
