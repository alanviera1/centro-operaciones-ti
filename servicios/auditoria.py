from flask import has_request_context
from flask_login import current_user

from modelos import Auditoria, bd


def usuario_actual():
    if has_request_context() and current_user.is_authenticated:
        return current_user._get_current_object()
    return None


def registrar_auditoria(accion, entidad, referencia=None, usuario=None):
    usuario = usuario or usuario_actual()
    bd.session.add(Auditoria(usuario=usuario, accion=accion, entidad=entidad, referencia=referencia))
