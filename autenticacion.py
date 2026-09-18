import secrets
from datetime import timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import LoginManager, current_user, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from modelos import ArchivoAcademico, Usuario, ahora, bd
from servicios.auditoria import registrar_auditoria

autenticacion = Blueprint('autenticacion', __name__)
gestor_login = LoginManager()
gestor_login.login_view = 'autenticacion.iniciar_sesion'
gestor_login.session_protection = 'strong'
hash_inexistente = generate_password_hash(secrets.token_urlsafe(24))


@gestor_login.user_loader
def cargar_usuario(identificador):
    if not identificador.isdigit():
        return None
    usuario = bd.session.get(Usuario, int(identificador))
    return usuario if usuario and usuario.activo else None


def exigir_supervisor():
    if not current_user.is_authenticated or current_user.rol != 'SUPERVISOR':
        abort(403, description='Esta operación requiere el rol Supervisor.')


@autenticacion.route('/login', methods=['GET', 'POST'])
def iniciar_sesion():
    if current_user.is_authenticated:
        return redirect(url_for('inicio'))
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip().lower()[:180]
        contrasena = request.form.get('contrasena', '')[:128]
        usuario = bd.session.scalar(bd.select(Usuario).where(Usuario.correo == correo).with_for_update())
        momento = ahora()
        bloqueado = usuario and usuario.bloqueado_hasta and usuario.bloqueado_hasta > momento
        valida = check_password_hash(usuario.contrasena_hash if usuario else hash_inexistente, contrasena)
        if usuario and usuario.activo and valida and not bloqueado:
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = None
            registrar_auditoria('SESION_INICIADA', 'usuarios', usuario.correo, usuario)
            bd.session.commit()
            session.clear()
            login_user(usuario, remember=False)
            session.permanent = True
            session['token_formulario'] = secrets.token_hex(24)
            session['ciclo_formulario'] = bd.session.scalar(bd.select(bd.func.coalesce(bd.func.max(ArchivoAcademico.id_archivo), 0)))
            flash(f'Bienvenido, {usuario.nombre}.', 'exito')
            return redirect(url_for('inicio'), code=303)
        if usuario and not bloqueado:
            if usuario.bloqueado_hasta:
                usuario.intentos_fallidos = 0
                usuario.bloqueado_hasta = None
            usuario.intentos_fallidos += 1
            if usuario.intentos_fallidos >= 5:
                usuario.bloqueado_hasta = momento + timedelta(minutes=5)
        registrar_auditoria('ACCESO_RECHAZADO', 'usuarios', 'Credenciales no válidas o acceso bloqueado')
        bd.session.commit()
        flash('No se pudo iniciar sesión. Revisa tus credenciales o espera cinco minutos si agotaste los intentos.', 'error')
        return render_template('login.html'), 401
    return render_template('login.html')


@autenticacion.post('/salir')
def cerrar_sesion():
    registrar_auditoria('SESION_CERRADA', 'usuarios', current_user.correo)
    bd.session.commit()
    logout_user()
    session.clear()
    return redirect(url_for('autenticacion.iniciar_sesion'), code=303)
