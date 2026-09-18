import os
import secrets
import logging
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from flask_login import current_user

from configuracion import Configuracion
from modelos import ArchivoAcademico, Auditoria, Componente, Evento, Incidente, Servicio, Usuario, ahora, bd
from servicios.gestor_eventos import REGLA_CORRELACION
from autenticacion import autenticacion, exigir_supervisor, gestor_login
from servicios.entorno_academico import restablecer_entorno
from servicios.gestor_disponibilidad import medir_servicio
from servicios.gestor_incidentes import acciones_disponibles, calcular_prioridad, ejecutar_accion
from servicios.simulador import ESCENARIOS, simular_eventos, prever_escenarios
from servicios.servicio_monitoreado import CONCIERTOS, DETALLES_CONCIERTOS, representar_servicio


def crear_aplicacion(configuracion=None):
    aplicacion = Flask(__name__, template_folder='plantillas', static_folder='estaticos')
    aplicacion.config.from_object(Configuracion)
    if configuracion:
        aplicacion.config.update(configuracion)
    if not aplicacion.config['SECRET_KEY']:
        raise ValueError('Configura SECRET_KEY en el entorno o en .env.')
    if aplicacion.config['ENTORNO'] == 'produccion' and len(aplicacion.config['SECRET_KEY']) < 32:
        raise ValueError('En producción SECRET_KEY debe tener al menos 32 caracteres aleatorios.')
    if aplicacion.config['ENTORNO'] == 'produccion':
        aplicacion.config.update(DEBUG=False, SESSION_COOKIE_SECURE=True)
    if aplicacion.config['MINUTOS_PERIODO'] <= 0 or aplicacion.config['VALOR_PROMEDIO_ENTRADA'] <= 0:
        raise ValueError('El período y valor promedio de entrada deben ser positivos.')
    bd.init_app(aplicacion)
    gestor_login.init_app(aplicacion)
    aplicacion.register_blueprint(autenticacion)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

    @aplicacion.before_request
    def verificar_formulario():
        publicas = ('static', 'autenticacion.iniciar_sesion', 'salud')
        if request.endpoint and request.endpoint not in publicas and not current_user.is_authenticated:
            return redirect(url_for('autenticacion.iniciar_sesion'))
        if current_user.is_authenticated:
            ciclo = bd.session.scalar(bd.select(bd.func.coalesce(bd.func.max(ArchivoAcademico.id_archivo), 0)))
            if session.get('ciclo_formulario') != ciclo:
                session['ciclo_formulario'] = ciclo
                session['token_formulario'] = secrets.token_hex(24)
        if 'token_formulario' not in session:
            session['token_formulario'] = secrets.token_hex(24)
        if request.method == 'POST':
            token = request.form.get('token_formulario', '')
            if not secrets.compare_digest(token, session['token_formulario']):
                abort(400, description='Formulario vencido o inválido. Actualiza la página e inténtalo nuevamente.')

    @aplicacion.after_request
    def proteger_respuesta(respuesta):
        respuesta.headers['X-Content-Type-Options'] = 'nosniff'
        respuesta.headers['X-Frame-Options'] = 'DENY'
        respuesta.headers['Referrer-Policy'] = 'same-origin'
        respuesta.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
        if request.endpoint != 'static':
            respuesta.headers['Cache-Control'] = 'no-store'
        if aplicacion.config['ENTORNO'] == 'produccion':
            respuesta.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return respuesta

    @aplicacion.context_processor
    def utilidades_plantillas():
        def enlace_pagina(numero):
            parametros = request.args.to_dict()
            parametros['pagina'] = numero
            return url_for(request.endpoint, **parametros)
        return dict(enlace_pagina=enlace_pagina, calcular_prioridad=calcular_prioridad,
                    regla_correlacion=REGLA_CORRELACION,
                    entorno_academico=aplicacion.config['ENTORNO_ACADEMICO'])

    @aplicacion.template_filter('fecha')
    def formatear_fecha(valor):
        if not valor:
            return 'Pendiente'
        if isinstance(valor, str):
            valor = datetime.fromisoformat(valor)
        return valor.astimezone(ZoneInfo('America/Lima')).strftime('%d/%m/%Y %H:%M:%S')

    @aplicacion.template_filter('numero')
    def formatear_numero(valor, decimales=0):
        return f'{float(valor):,.{decimales}f}'

    @aplicacion.template_filter('etiqueta')
    def etiqueta(valor):
        etiquetas = {'ABIERTO': 'Detectado', 'CAIDO': 'Caído', 'CRITICA': 'Crítica', 'CRITICO': 'Crítico',
                     'EN_PROCESO': 'En proceso', 'SERVICIO_RECUPERADO': 'Servicio recuperado',
                     'OPERATIVO_CON_RESPALDO': 'Operativo con respaldo',
                     'RESPALDO_ACTIVO': 'Respaldo activo', 'EN_RIESGO': 'En riesgo',
                     'SESION_INICIADA': 'Sesión iniciada', 'SESION_CERRADA': 'Sesión cerrada',
                     'SESION_RECHAZADA': 'Sesión rechazada', 'SIMULACION_EJECUTADA': 'Simulación ejecutada'}
        return etiquetas.get(valor, valor.replace('_', ' ').capitalize())

    def obtener_servicio(bloquear=False):
        consulta = bd.select(Servicio).order_by(Servicio.id_servicio).limit(1)
        if bloquear:
            consulta = consulta.with_for_update()
        servicio = bd.session.scalar(consulta)
        if servicio is None:
            abort(503, description='Falta preparar la base. Ejecuta preparar_bd.py.')
        if bloquear and current_user.is_authenticated:
            ciclo = bd.session.scalar(bd.select(bd.func.coalesce(bd.func.max(ArchivoAcademico.id_archivo), 0)))
            if session.get('ciclo_formulario') != ciclo:
                abort(400, description='El entorno se restableció. Actualiza la página antes de continuar.')
        return servicio

    def leer_entero(campo, predeterminado):
        try:
            return int(request.form.get(campo, predeterminado))
        except ValueError:
            raise ValueError(f'El campo {campo} debe contener un número entero.') from None

    @aplicacion.get('/')
    def inicio():
        servicio = obtener_servicio()
        metricas = medir_servicio(servicio)
        eventos = bd.session.scalars(bd.select(Evento).where(Evento.archivado.is_(False))
                                     .order_by(Evento.fecha_hora.desc(), Evento.id_evento.desc()).limit(5)).all()
        return render_template('inicio.html', servicio=servicio, metricas=metricas, eventos=eventos,
                               escenarios=ESCENARIOS, valor_entrada=aplicacion.config['VALOR_PROMEDIO_ENTRADA'])

    def consultar_incidentes(historico):
        consulta = bd.select(Incidente).options(selectinload(Incidente.componente),
            selectinload(Incidente.responsable), selectinload(Incidente.acciones))
        if historico:
            consulta = consulta.where(Incidente.estado == 'CERRADO')
            if request.args.get('archivados') != '1':
                consulta = consulta.where(Incidente.archivado.is_(False))
        else:
            consulta = consulta.where(Incidente.estado != 'CERRADO', Incidente.archivado.is_(False))
            estado = request.args.get('estado', '')
            if estado in ('ABIERTO', 'EN_PROCESO', 'RESUELTO'):
                consulta = consulta.where(Incidente.estado == estado)
        prioridad = request.args.get('prioridad', '')
        if prioridad in ('BAJA', 'MEDIA', 'ALTA', 'CRITICA'):
            consulta = consulta.where(Incidente.prioridad == prioridad)
        componente = request.args.get('componente', type=int)
        if componente:
            consulta = consulta.where(Incidente.id_componente == componente)
        codigo = request.args.get('codigo', '').strip()[:35]
        if codigo:
            consulta = consulta.where(Incidente.codigo_incidente.icontains(codigo, autoescape=True))
        pagina = bd.paginate(consulta.order_by(Incidente.fecha_inicio.desc(), Incidente.id_incidente.desc()),
                             page=max(1, request.args.get('pagina', 1, type=int)), per_page=12, error_out=False)
        componentes = bd.session.scalars(bd.select(Componente).order_by(Componente.id_componente)).all()
        return render_template('historial.html' if historico else 'incidentes.html',
                               pagina=pagina, componentes=componentes)

    @aplicacion.get('/incidentes')
    def listar_incidentes():
        return consultar_incidentes(False)

    @aplicacion.get('/historial')
    def historial():
        if request.args.get('archivados') == '1':
            return archivo_academico()
        return consultar_incidentes(True)

    @aplicacion.get('/archivo-academico')
    def archivo_academico():
        pagina = bd.paginate(bd.select(ArchivoAcademico).order_by(ArchivoAcademico.id_archivo.desc()),
                             page=max(1, request.args.get('pagina', 1, type=int)), per_page=10, error_out=False)
        return render_template('archivo_academico.html', pagina=pagina, archivo=None)

    @aplicacion.get('/archivo-academico/<int:identificador>')
    def detalle_archivo(identificador):
        archivo = bd.get_or_404(ArchivoAcademico, identificador)
        return render_template('archivo_academico.html', archivo=archivo, pagina=None)

    @aplicacion.get('/simulador')
    def laboratorio():
        if not aplicacion.config['ENTORNO_ACADEMICO']:
            abort(403, description='El laboratorio está desactivado en este entorno.')
        return render_template('simulador.html', escenarios=ESCENARIOS,
                               previsiones=prever_escenarios(obtener_servicio()))

    @aplicacion.get('/simulador/prevision')
    def prevision_simulador():
        if not aplicacion.config['ENTORNO_ACADEMICO']:
            abort(403, description='El laboratorio está desactivado en este entorno.')
        return prever_escenarios(obtener_servicio())

    def estado_preview(servicio):
        estado = representar_servicio(servicio)
        metricas = medir_servicio(servicio)
        estado.update(disponibilidad=f"{metricas['disponibilidad']:.3f}",
                      estado_sla=metricas['estado_sla'],
                      texto_sla='SLA del período: cumplido' if metricas['estado_sla'] == 'CUMPLIDO' else 'SLA del período: incumplido',
                      objetivo_sla=f'{servicio.sla_objetivo:.2f}',
                      actualizado=ahora().astimezone(ZoneInfo('America/Lima')).strftime('%H:%M:%S'))
        return estado

    @aplicacion.get('/servicio-monitoreado/estado')
    def estado_servicio_monitoreado():
        return estado_preview(obtener_servicio())

    @aplicacion.route('/servicio-monitoreado', methods=['GET', 'POST'])
    def servicio_monitoreado():
        servicio = obtener_servicio(bloquear=request.method == 'POST')
        representacion = estado_preview(servicio)
        resultado = session.pop('resultado_preview', None)
        estado_http = 200
        if request.method == 'POST':
            accion = request.form.get('accion')
            if accion not in ('iniciar', 'comprar'):
                abort(400, description='Acción simulada no válida.')
            if accion == 'comprar' and request.form.get('concierto') not in dict((c[0], c[1]) for c in CONCIERTOS):
                abort(400, description='Concierto de ejemplo no válido.')
            permitido = representacion['puede_iniciar' if accion == 'iniciar' else 'puede_comprar']
            concierto = dict((c[0], c[1]) for c in CONCIERTOS).get(request.form.get('concierto'), '')
            resultado = dict(tipo='entrada' if permitido and accion == 'comprar' else 'acceso' if permitido else 'bloqueo',
                titulo=f'Tu pase de muestra para {concierto}' if permitido and accion == 'comprar' else
                       'Puedes acceder a Ritmo' if permitido else 'No pudimos completar la operación',
                mensaje='Compra simulada completada. Entrada general · 1 persona. Sin cobro ni reserva; este pase no es válido para ingresar a un evento.' if permitido and accion == 'comprar' else
                        'Autenticación disponible. Inicio simulado permitido; no se ha creado una cuenta ni modificado tu sesión del Centro de Operaciones TI.' if permitido else
                        representacion['motivo_compra' if accion == 'comprar' else 'motivo_acceso'])
            if request.accept_mimetypes.best == 'application/json':
                return dict(resultado=resultado, estado=representacion), 200 if permitido else 409
            if permitido:
                session['resultado_preview'] = resultado
                return redirect(url_for('servicio_monitoreado'), code=303)
            estado_http = 409
        return render_template('servicio_monitoreado.html', representacion=representacion,
                               conciertos=CONCIERTOS, detalles=DETALLES_CONCIERTOS, resultado=resultado, servicio=servicio,
                               metricas=medir_servicio(servicio)), estado_http

    @aplicacion.get('/incidentes/<int:identificador>')
    def detalle_incidente(identificador):
        incidente = bd.get_or_404(Incidente, identificador, description='El incidente solicitado no existe.')
        metricas = medir_servicio(incidente.componente.servicio)
        caida = 0
        for interrupcion in incidente.interrupciones:
            caida += ((interrupcion.fecha_fin or ahora()) - interrupcion.fecha_inicio).total_seconds() / 60
        return render_template('detalle_incidente.html', incidente=incidente,
                               acciones=acciones_disponibles(incidente), metricas=metricas, caida=caida)

    @aplicacion.get('/eventos')
    def listar_eventos():
        if request.args.get('archivados') == '1':
            return archivo_academico()
        consulta = bd.select(Evento).options(selectinload(Evento.componente), selectinload(Evento.incidente))
        if request.args.get('archivados') != '1':
            consulta = consulta.where(Evento.archivado.is_(False))
        nivel = request.args.get('nivel', '')
        if nivel in ('INFORMATIVO', 'ADVERTENCIA', 'CRITICO'):
            consulta = consulta.where(Evento.nivel == nivel)
        componente = request.args.get('componente', type=int)
        if componente:
            consulta = consulta.where(Evento.id_componente == componente)
        fecha = request.args.get('fecha', '')
        if fecha:
            try:
                inicio_fecha = datetime.combine(date.fromisoformat(fecha), time(), ZoneInfo('America/Lima'))
            except ValueError:
                abort(400, description='La fecha debe tener el formato año-mes-día.')
            consulta = consulta.where(Evento.fecha_hora >= inicio_fecha, Evento.fecha_hora < inicio_fecha + timedelta(days=1))
        pagina = bd.paginate(consulta.order_by(Evento.fecha_hora.desc(), Evento.id_evento.desc()),
                              page=max(1, request.args.get('pagina', 1, type=int)), per_page=15, error_out=False)
        componentes = bd.session.scalars(bd.select(Componente).order_by(Componente.id_componente)).all()
        return render_template('eventos.html', pagina=pagina, componentes=componentes)

    @aplicacion.post('/simulaciones/<nombre>')
    def simular(nombre):
        if not aplicacion.config['ENTORNO_ACADEMICO']:
            abort(403, description='Las simulaciones están desactivadas en este entorno.')
        try:
            servicio = obtener_servicio(bloquear=True)
            impacto = leer_entero('impacto', 2)
            urgencia = leer_entero('urgencia', 3)
            minutos = leer_entero('minutos', 5)
            incidente = simular_eventos(servicio, nombre, impacto, urgencia, minutos)
            bd.session.commit()
        except ValueError as error:
            bd.session.rollback()
            flash(str(error), 'error')
            return redirect(url_for('laboratorio'), code=303)
        if incidente:
            flash(f'Eventos guardados y correlacionados con {incidente.numero}. Prioridad {incidente.prioridad}.', 'exito')
        else:
            flash('Advertencia guardada. ' + REGLA_CORRELACION, 'aviso')
        if incidente:
            return redirect(url_for('detalle_incidente', identificador=incidente.id_incidente), code=303)
        return redirect(url_for('laboratorio'), code=303)

    @aplicacion.post('/incidentes/<int:identificador>/acciones')
    def realizar_accion(identificador):
        accion = request.form.get('accion', '')
        if accion == 'cerrar':
            exigir_supervisor()
        if accion == 'escalar' and current_user.rol != 'OPERADOR':
            abort(403, description='Solo un operador puede escalar incidentes.')
        obtener_servicio(bloquear=True)
        incidente = bd.get_or_404(Incidente, identificador, description='El incidente solicitado no existe.')
        try:
            ejecutar_accion(incidente, accion)
            bd.session.commit()
            mensajes = {'iniciar': 'Atención iniciada.', 'activar_respaldo': 'Respaldo activado. Servicio recuperado.',
                        'resolver': 'Incidente resuelto.', 'cerrar': 'Servicio normalizado e incidente cerrado.',
                        'reiniciar': 'Componente reiniciado.', 'escalar': 'Incidente escalado.'}
            flash(mensajes[accion], 'exito')
        except ValueError as error:
            bd.session.rollback()
            flash(str(error), 'error')
        return redirect(url_for('detalle_incidente', identificador=identificador), code=303)

    @aplicacion.post('/entorno/restablecer')
    def restablecer():
        exigir_supervisor()
        if not aplicacion.config['ENTORNO_ACADEMICO']:
            abort(403, description='El restablecimiento académico está desactivado.')
        if request.form.get('confirmacion') != 'RESTABLECER':
            abort(400, description='Debes confirmar explícitamente el restablecimiento.')
        try:
            cantidad = restablecer_entorno(obtener_servicio(bloquear=True))
            bd.session.commit()
            flash(f'Entorno restablecido. {cantidad} incidentes conservados en ciclos anteriores. La numeración vuelve a 0001.', 'exito')
        except ValueError as error:
            bd.session.rollback()
            flash(str(error), 'error')
        return redirect(url_for('laboratorio'), code=303)

    @aplicacion.get('/auditoria')
    def auditoria():
        exigir_supervisor()
        consulta = bd.select(Auditoria).options(selectinload(Auditoria.usuario))
        accion = request.args.get('accion', '').strip()
        if accion:
            consulta = consulta.where(Auditoria.accion == accion)
        usuario = request.args.get('usuario', '')
        if usuario == 'sistema':
            consulta = consulta.where(Auditoria.id_usuario.is_(None))
        elif usuario:
            try:
                consulta = consulta.where(Auditoria.id_usuario == int(usuario))
            except ValueError:
                abort(400, description='Selecciona un usuario válido.')
        referencia = request.args.get('referencia', '').strip()[:120]
        if referencia:
            consulta = consulta.where(Auditoria.referencia.icontains(referencia, autoescape=True))
        fecha = request.args.get('fecha', '')
        if fecha:
            try:
                inicio_fecha = datetime.combine(date.fromisoformat(fecha), time(), ZoneInfo('America/Lima'))
            except ValueError:
                abort(400, description='La fecha debe tener el formato año-mes-día.')
            consulta = consulta.where(Auditoria.fecha_hora >= inicio_fecha,
                                      Auditoria.fecha_hora < inicio_fecha + timedelta(days=1))
        pagina = bd.paginate(consulta
            .order_by(Auditoria.fecha_hora.desc(), Auditoria.id_auditoria.desc()),
            page=max(1, request.args.get('pagina', 1, type=int)), per_page=20, error_out=False)
        acciones = bd.session.scalars(bd.select(Auditoria.accion).distinct().order_by(Auditoria.accion)).all()
        usuarios = bd.session.scalars(bd.select(Usuario).order_by(Usuario.nombre)).all()
        return render_template('auditoria.html', pagina=pagina, acciones=acciones, usuarios=usuarios)

    @aplicacion.get('/salud')
    def salud():
        bd.session.execute(bd.text('SELECT 1'))
        return {'estado': 'operativo'}

    @aplicacion.errorhandler(SQLAlchemyError)
    def error_base_datos(error):
        bd.session.rollback()
        aplicacion.logger.error('Operación de base de datos fallida: %s', type(error).__name__)
        if request.endpoint == 'salud':
            return {'estado': 'no_disponible'}, 503
        return render_template('error.html', codigo=503,
                               mensaje='No se pudo completar la operación. Revisa la conexión PostgreSQL e inténtalo nuevamente.'), 503

    @aplicacion.errorhandler(400)
    @aplicacion.errorhandler(403)
    @aplicacion.errorhandler(404)
    @aplicacion.errorhandler(405)
    @aplicacion.errorhandler(413)
    @aplicacion.errorhandler(503)
    def error_pagina(error):
        mensaje = error.description
        if error.code == 404 and mensaje.startswith('The requested'):
            mensaje = 'La página solicitada no existe.'
        if error.code == 405:
            mensaje = 'Método no permitido para esta operación.'
        if error.code == 413:
            mensaje = 'El formulario excede el tamaño permitido.'
        return render_template('error.html', codigo=error.code, mensaje=mensaje), error.code

    return aplicacion


if __name__ == '__main__':
    from waitress import serve
    aplicacion = crear_aplicacion()
    puerto = int(os.getenv('PUERTO', '5055'))
    print(f'Centro de Operaciones TI disponible en http://127.0.0.1:{puerto}', flush=True)
    serve(aplicacion, host='127.0.0.1', port=puerto, threads=4)
