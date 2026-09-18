const botonTema = document.querySelector('.boton-tema');
function actualizarBotonTema() {
  const oscuro = document.documentElement.dataset.tema === 'oscuro';
  botonTema.textContent = oscuro ? '☀' : '☾';
  botonTema.setAttribute('aria-label', oscuro ? 'Activar modo claro' : 'Activar modo oscuro');
}
actualizarBotonTema();
botonTema.addEventListener('click', function () {
  const tema = document.documentElement.dataset.tema === 'oscuro' ? 'claro' : 'oscuro';
  document.documentElement.dataset.tema = tema;
  try { localStorage.setItem('escudo_ti_tema', tema); } catch (error) { /* Preferencia temporal. */ }
  actualizarBotonTema();
});

const modal = document.getElementById('confirmacion');
let formularioPendiente = null;
let botonOrigen = null;
function cerrarConfirmacion() {
  modal.close();
  if (botonOrigen) botonOrigen.focus();
  formularioPendiente = null;
}
document.getElementById('cancelar-confirmacion').addEventListener('click', cerrarConfirmacion);
modal.addEventListener('cancel', function () { formularioPendiente = null; });
document.getElementById('aceptar-confirmacion').addEventListener('click', function () {
  const formulario = formularioPendiente;
  cerrarConfirmacion();
  if (formulario) {
    formulario.dataset.confirmado = 'si';
    formulario.requestSubmit();
  }
});
document.querySelectorAll('form[method="post"]').forEach(function (formulario) {
  if (formulario.hasAttribute('data-operacion-ritmo')) return;
  formulario.addEventListener('submit', function (evento) {
    if (formulario.dataset.confirmar && formulario.dataset.confirmado !== 'si') {
      evento.preventDefault();
      formularioPendiente = formulario;
      botonOrigen = evento.submitter;
      document.getElementById('titulo-confirmacion').textContent = formulario.dataset.titulo || 'Confirmar acción';
      document.getElementById('texto-confirmacion').textContent = formulario.dataset.confirmar;
      document.getElementById('aceptar-confirmacion').textContent = formulario.dataset.boton || 'Confirmar';
      modal.showModal();
      document.getElementById('cancelar-confirmacion').focus();
      return;
    }
    formulario.querySelectorAll('button[type="submit"]').forEach(function (boton) {
      boton.dataset.textoOriginal = boton.textContent;
      boton.disabled = true;
      boton.textContent = 'Procesando…';
    });
  });
});
window.addEventListener('pageshow', function () {
  document.querySelectorAll('button[data-texto-original]').forEach(function (boton) {
    boton.disabled = false;
    boton.textContent = boton.dataset.textoOriginal;
  });
  document.querySelectorAll('form[data-confirmado]').forEach(function (formulario) {
    delete formulario.dataset.confirmado;
  });
});
document.querySelectorAll('.toast').forEach(function (aviso) {
  aviso.querySelector('button').addEventListener('click', function () { aviso.remove(); });
  window.setTimeout(function () { if (!aviso.matches(':hover, :focus-within')) aviso.remove(); }, 9000);
});

const escenariosDinamicos = document.querySelector('[data-url-prevision]');
if (escenariosDinamicos) {
  const etiquetasPrioridad = { BAJA: 'Baja', MEDIA: 'Media', ALTA: 'Alta', CRITICA: 'Crítica' };
  function actualizarPrioridad(tarjeta) {
    const impacto = tarjeta.querySelector('[name="impacto"]')?.value || tarjeta.dataset.impacto;
    const urgencia = tarjeta.querySelector('[name="urgencia"]')?.value || tarjeta.dataset.urgencia;
    const prioridades = JSON.parse(tarjeta.dataset.prioridades);
    tarjeta.querySelector('[data-prioridad-prevision]').textContent = 'Prioridad prevista: ' + etiquetasPrioridad[prioridades[impacto + '-' + urgencia]];
  }
  escenariosDinamicos.querySelectorAll('[data-escenario]').forEach(function (tarjeta) {
    tarjeta.querySelectorAll('select').forEach(function (campo) {
      campo.addEventListener('change', function () { actualizarPrioridad(tarjeta); });
    });
    actualizarPrioridad(tarjeta);
  });
  let consultandoPrevision = false;
  async function consultarPrevision() {
    if (document.hidden || consultandoPrevision) return;
    consultandoPrevision = true;
    try {
      const respuesta = await fetch(escenariosDinamicos.dataset.urlPrevision, { headers: { Accept: 'application/json' } });
      if (!respuesta.ok) throw new Error('Previsión no disponible');
      const previsiones = await respuesta.json();
      escenariosDinamicos.querySelectorAll('[data-escenario]').forEach(function (tarjeta) {
        const prevision = previsiones[tarjeta.dataset.escenario];
        tarjeta.dataset.prioridades = JSON.stringify(prevision.prioridades);
        tarjeta.querySelector('[data-mensaje-prevision]').textContent = prevision.mensaje;
        tarjeta.querySelector('[data-titulo-prevision]').textContent = prevision.bloqueado ? 'Estado actual' : 'Resultado previsto';
        tarjeta.querySelector('form').hidden = prevision.bloqueado;
        const enlace = tarjeta.querySelector('[data-incidente-prevision]');
        enlace.hidden = !prevision.incidente_id;
        enlace.textContent = prevision.enlace_incidente;
        enlace.href = prevision.incidente_id ? '/incidentes/' + prevision.incidente_id : '#';
        tarjeta.querySelector('[data-prioridad-prevision]').hidden = prevision.bloqueado;
        const boton = tarjeta.querySelector('button[type="submit"]');
        if (!boton.dataset.textoOriginal) boton.disabled = prevision.bloqueado;
        actualizarPrioridad(tarjeta);
      });
      document.querySelector('[data-estado-prevision]').textContent = 'Previsión actualizada desde PostgreSQL. Se vuelve a validar al ejecutar.';
    } catch (error) {
      document.querySelector('[data-estado-prevision]').textContent = 'No se pudo actualizar la previsión. Recarga la página para consultar el estado actual.';
    } finally { consultandoPrevision = false; }
  }
  window.setInterval(consultarPrevision, 10000);
  document.addEventListener('visibilitychange', consultarPrevision);
}
