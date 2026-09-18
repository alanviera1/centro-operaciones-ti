from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from conftest import ingresar
from modelos import Auditoria, Evento, Usuario, ahora, bd, generar_codigo
from servicios.entorno_academico import restablecer_entorno
from servicios.gestor_eventos import REGLA_CORRELACION, correlacionar_eventos
from servicios.simulador import ESCENARIOS, simular_eventos


@pytest.mark.parametrize('criticos,advertencias,esperado', [(1, 0, True), (0, 2, False), (0, 3, True)])
def test_umbral_real_correlacion(contexto, criticos, advertencias, esperado):
    _, servicio = contexto
    restablecer_entorno(servicio)
    componente = next(c for c in servicio.componentes if c.tipo == 'BD')
    for nivel, cantidad in [('CRITICO', criticos), ('ADVERTENCIA', advertencias)]:
        for _ in range(cantidad):
            bd.session.add(Evento(componente=componente, tipo='PRUEBA', descripcion='Señal de prueba', nivel=nivel))
    bd.session.add(Evento(componente=componente, tipo='ANTIGUO', descripcion='Fuera de ventana',
                         nivel='CRITICO', fecha_hora=ahora() - timedelta(minutes=6)))
    incidente = correlacionar_eventos(componente, ESCENARIOS['base_datos'], 2, 3, 0)
    assert (incidente is not None) == esperado
    if incidente:
        assert len(incidente.eventos) == criticos + advertencias


def test_codigo_usa_anio_lima_y_cuatro_digitos():
    conexion = SimpleNamespace(execute=lambda consulta: SimpleNamespace(scalar_one=lambda: 48))
    contexto = SimpleNamespace(connection=conexion, get_current_parameters=lambda: {
        'fecha_inicio': datetime(2027, 1, 1, 2, tzinfo=timezone.utc)})
    assert generar_codigo(contexto) == 'INC-2026-0048'


def test_normalizacion_preserva_pk_acciones_y_auditoria(contexto):
    _, servicio = contexto
    incidente = simular_eventos(servicio, 'pagos')
    bd.session.flush()
    identificador = incidente.id_incidente
    numero = int(incidente.codigo_incidente.split('-')[2])
    anterior = f'INC-2026-{numero:06d}'
    incidente.codigo_incidente = anterior
    registro = Auditoria(accion='PRUEBA', entidad='incidentes', referencia=anterior)
    bd.session.add(registro)
    bd.session.flush()
    acciones = [a.id_accion for a in incidente.acciones]
    archivo = Path(__file__).resolve().parents[1] / 'migraciones/002_codigos_uniformes.sql'
    for sentencia in archivo.read_text(encoding='utf-8').split(';'):
        if sentencia.strip():
            bd.session.execute(text(sentencia))
    bd.session.expire_all()
    assert incidente.id_incidente == identificador
    assert incidente.codigo_incidente == f'INC-{incidente.fecha_inicio.astimezone(ZoneInfo("America/Lima")).year}-{numero:04d}'
    assert registro.referencia == incidente.codigo_incidente
    assert [a.id_accion for a in incidente.acciones] == acciones


def test_auditoria_filtra_y_pagina_por_fecha_lima(contexto):
    aplicacion, _ = contexto
    usuario = bd.session.scalar(bd.select(Usuario).where(Usuario.correo == 'supervisor@pruebas.local'))
    for numero in range(23):
        bd.session.add(Auditoria(id_usuario=usuario.id_usuario, accion='PRUEBA_FILTROS', entidad='incidentes',
            referencia=f'INC-2026-{9000+numero:04d}', fecha_hora=datetime(2026, 1, 2, 2, tzinfo=timezone.utc)))
    bd.session.commit()
    cliente = aplicacion.test_client()
    ingresar(cliente)
    ruta = f'/auditoria?accion=PRUEBA_FILTROS&usuario={usuario.id_usuario}&referencia=INC-2026-90&fecha=2026-01-01'
    primera = cliente.get(ruta).text
    segunda = cliente.get(ruta + '&pagina=2').text
    assert primera.count('<strong>Prueba filtros</strong>') == 20
    assert segunda.count('<strong>Prueba filtros</strong>') == 3
    assert 'fecha=2026-01-01' in primera and 'pagina=2' in primera
    assert 'Sin registros para estos filtros' in cliente.get(ruta.replace('2026-01-01','2026-01-02')).text
    assert 'Sin registros para estos filtros' in cliente.get('/auditoria?referencia=%25').text
    assert cliente.get('/auditoria?fecha=incorrecta').status_code == 400


def test_textos_visibles_consistentes(contexto):
    aplicacion, _ = contexto
    cliente = aplicacion.test_client()
    ingresar(cliente)
    for ruta in ('/eventos', '/simulador'):
        assert REGLA_CORRELACION in cliente.get(ruta).text
    panel = cliente.get('/').text
    assert 'CENTRO DE OPERACIONES TI' in panel
    assert 'GESTIÓN DEL SERVICIO TI' in panel
    assert 'ESCUDO TI' not in panel
    assert '24 × 7' not in panel
    assert 'Incidentes por atender o cerrar' in panel
    assert 'resueltos pendientes de cierre' in panel
    assert '>v2<' not in panel
