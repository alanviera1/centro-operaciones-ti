/* La preview consulta el mismo estado que valida cada operación en el servidor. */
(() => {
  'use strict';
  const marco = document.querySelector('#preview-ritmo');
  if (!marco) return;
  const sitio = marco.querySelector('#ritmo-sitio');
  const formularios = [...marco.querySelectorAll('[data-operacion-ritmo]')];
  const resultado = marco.querySelector('#ritmo-resultado');
  const conexion = marco.querySelector('#ritmo-conexion');
  const recargar = marco.querySelector('#ritmo-recargar');
  let ocupado = false;
  let vencido = false;
  let origenResultado = null;
  const bloquear = () => formularios.forEach(f => { f.querySelector('button').disabled = true; });
  function pintar(estado) {
    sitio.dataset.tono = estado.tono;
    sitio.dataset.web = estado.web ? 'activa' : 'caida';
    marco.querySelectorAll('[data-campo]').forEach(nodo => {
      if (Object.hasOwn(estado, nodo.dataset.campo)) nodo.textContent = estado[nodo.dataset.campo];
    });
    for (const accion of ['compra', 'acceso']) {
      const motivo = marco.querySelector(`#ritmo-motivo-${accion}`);
      motivo.textContent = estado[`motivo_${accion}`];
      motivo.hidden = estado[accion === 'compra' ? 'puede_comprar' : 'puede_iniciar'];
    }
    formularios.forEach(f => {
      f.querySelector('button').disabled = vencido || !estado[f.dataset.operacionRitmo === 'comprar' ? 'puede_comprar' : 'puede_iniciar'];
    });
    conexion.textContent = `Actualizado ${estado.actualizado} · Consulta automática cada 5 s`;
  }
  function mostrar(datos) {
    resultado.dataset.tipo = datos.tipo;
    resultado.querySelector('[data-resultado-titulo]').textContent = datos.titulo;
    resultado.querySelector('[data-resultado-mensaje]').textContent = datos.mensaje;
    resultado.hidden = false;
    resultado.focus({preventScroll: true});
    resultado.scrollIntoView({block: 'center', behavior: 'auto'});
  }
  function fallo() {
    bloquear();
    sitio.dataset.tono = 'error';
    marco.querySelector('[data-campo=titulo_aviso]').textContent = 'No podemos confirmar el estado';
    marco.querySelector('[data-campo=mensaje]').textContent = 'Las operaciones están pausadas hasta recuperar la conexión.';
    conexion.textContent = 'Sin actualizar. Los últimos datos mostrados pueden haber cambiado.';
    recargar.hidden = false;
  }
  async function consultar() {
    if (ocupado || document.hidden || vencido) return;
    ocupado = true;
    try {
      const respuesta = await fetch(marco.dataset.estadoUrl, {headers: {Accept: 'application/json'}, signal: AbortSignal.timeout(8000)});
      if (!respuesta.ok || !respuesta.headers.get('content-type')?.includes('application/json')) throw new Error('sesion');
      pintar(await respuesta.json());
      recargar.hidden = true;
    } catch { fallo(); }
    finally { ocupado = false; }
  }
  formularios.forEach(formulario => formulario.addEventListener('submit', async evento => {
    evento.preventDefault();
    if (ocupado || vencido) return;
    ocupado = true;
    origenResultado = evento.submitter || formulario.querySelector('button');
    bloquear();
    formulario.setAttribute('aria-busy', 'true');
    try {
      const respuesta = await fetch(formulario.action, {method: 'POST', body: new FormData(formulario), headers: {Accept: 'application/json'}, signal: AbortSignal.timeout(8000)});
      if (respuesta.status === 400 || respuesta.redirected) vencido = true;
      if (!respuesta.headers.get('content-type')?.includes('application/json')) throw new Error('sesion');
      const datos = await respuesta.json();
      if (![200, 409].includes(respuesta.status)) throw new Error('conexion');
      pintar(datos.estado);
      mostrar(datos.resultado);
    } catch {
      fallo();
      mostrar({tipo: 'bloqueo', titulo: vencido ? 'Esta vista necesita actualizarse' : 'La operación no pudo confirmarse', mensaje: vencido ? 'La sesión o el ciclo académico cambió. Recarga la vista antes de continuar.' : 'No se ha realizado ningún cobro. Actualiza el estado para volver a intentarlo.'});
    } finally { ocupado = false; formulario.removeAttribute('aria-busy'); }
  }));
  marco.querySelector('#ritmo-cerrar-resultado').addEventListener('click', () => {
    resultado.hidden = true;
    (origenResultado && !origenResultado.disabled ? origenResultado : marco.querySelector('#ritmo-actualizar')).focus();
  });
  const expandir = marco.querySelector('#ritmo-expandir');
  let desplazamiento = 0;
  function ampliar(valor) {
    if (valor) desplazamiento = window.scrollY;
    document.body.classList.toggle('ritmo-ampliada', valor);
    expandir.setAttribute('aria-expanded', String(valor));
    expandir.textContent = valor ? 'Contraer vista ↙' : 'Ampliar vista ↗';
    window.scrollTo(0, valor ? 0 : desplazamiento);
    expandir.focus({preventScroll: true});
  }
  expandir.addEventListener('click', () => ampliar(expandir.getAttribute('aria-expanded') !== 'true'));
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && expandir.getAttribute('aria-expanded') === 'true') ampliar(false);
  });
  marco.querySelector('#ritmo-actualizar').addEventListener('click', consultar);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) consultar(); });
  setInterval(consultar, 5000);
})();
