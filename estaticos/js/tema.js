(function () {
  let preferencia;
  try { preferencia = localStorage.getItem('escudo_ti_tema'); } catch (error) { preferencia = null; }
  const oscuro = preferencia ? preferencia === 'oscuro' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  document.documentElement.dataset.tema = oscuro ? 'oscuro' : 'claro';
})();
