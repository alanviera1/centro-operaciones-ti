# Verificación final — CENTRO DE OPERACIONES TI v2.1

Fecha: 18/09/2026. Mejora controlada de la preview y del restablecimiento académico. Sin despliegue.

## Cambios y alcance

Ritmo Entradas tiene identidad visual propia: banner, carteles de conciertos, precios ficticios, llamadas a la acción, modo claro/oscuro y vista ampliada reversible (también con Escape). Es una representación académica, sin venta, cobro, reserva ni cuentas reales.

La preview consulta PostgreSQL cada cinco segundos y al operar. Muestra disponibilidad, web principal, pagos y autenticación. Bloquea compra ante pagos, autenticación, BD o web no disponibles; bloquea acceso ante autenticación, BD o web no disponibles. Un respaldo activo permite continuidad y muestra contingencia. La pérdida de conexión pausa operaciones. Feedback separado para pase de muestra, acceso y bloqueo. Los formularios conservan funcionamiento sin JavaScript mediante recarga.

El reset conserva tablas operativas, contexto de componentes y nombres/roles de autores en archivo_academico. No incluye hashes ni credenciales. Luego vacía eventos, incidentes, acciones_incidente, interrupciones y auditoría; reinicia sus secuencias y la secuencia independiente del código a 1. Restaura servicio y componentes. Inserta una constancia ENTORNO_RESTABLECIDO en la nueva auditoría.

El archivo mantiene estados y tiempos originales; un incidente pendiente no aparece falsamente recuperado. Cada ciclo se consulta separado del historial actual. Código único en la operación; ciclo + código identifica evidencia archivada. Los formularios antiguos caducan tras el reset para impedir acciones sobre una PK reutilizada. El reset exige supervisor, confirmación explícita, modo académico, un único servicio y datos exclusivamente académicos. Todo ocurre en una transacción.

Se añadió la migración 003_archivo_academico.sql; no se cambiaron PK/FK existentes ni la regla de correlación:

Un evento crítico o tres advertencias del mismo componente en cinco minutos generan un incidente. Se consideran eventos sin atender, no archivados y aún sin incidente.

## Respaldo

Respaldo privado anterior a esta mejora: ../respaldo_preview_20260918_072318, con código, escudo_ti.dump y datos.json. Se restauró realmente con pg_restore --exit-on-error en una base temporal y se compararon todas las filas de las nueve tablas originales. Resultado idéntico; base temporal retirada. VERIFICACION_RESTAURACION.json registra SHA256 y conteos.

El respaldo conserva 1 incidente, 4 eventos, 6 acciones, 1 interrupción y 7 registros de auditoría, además de 2 usuarios, 1 servicio, 6 componentes y las 2 versiones de esquema anteriores. Los respaldos pre-v2, pre-v2.1 y de exposición anteriores se mantienen.

## Pruebas

- Suite completa: **53 passed in 21.80s**, PostgreSQL real.
- Casos nuevos: dos ciclos consecutivos con PK 1 y código 0001; fechas/autores preservados; archivo sin hashes; reinicio de secuencias; rollback tras fallo posterior a TRUNCATE; rechazo de eventos no académicos; bloqueo de formulario anterior al reset; permisos del archivo; preview JSON ante fallos y recuperación de pagos, autenticación, servidor y BD.
- compileall: correcto.
- pip check: No broken requirements found.
- node --check: correcto en los dos scripts modificados.
- HTTP contra Waitress: login → reset → pagos INC-2026-0001 → compra bloqueada 409 → respaldo → pase simulado → resolver → cerrar → restaurar principal → reset final. La restauración del principal se ejecuta después de resolver/cerrar, conforme al flujo existente.
- Lecturas HTTP correctas de dashboard, preview/estado, eventos, incidentes, historial, auditoría y ambos ciclos del archivo.

Evidencia resumida: evidencias/preview_reset_http.json.

## Estado final de PostgreSQL

- Eventos: 0; incidentes: 0; acciones: 0; interrupciones: 0.
- Auditoría: 1 constancia del reset final. Su secuencia se reinició y esa constancia ocupa el primer valor.
- Ciclos anteriores: evidencia separada de ciclos de demostración y validación HTTP.
- Usuarios: 2, comparados íntegramente con el respaldo; hashes y atributos intactos.
- Servicio: 1; componentes: 6, todos operativos; SLA 99.90 %; disponibilidad 100.000 %.
- Migraciones aplicadas: 3. Restricciones PostgreSQL validadas; no se detectaron relaciones inválidas.
- Evidencia original de incidentes, eventos, acciones e interrupciones comparada exactamente con el primer archivo.
- secuencia_codigo_incidente: last_value=1, is_called=false, comprobado sin nextval. **El siguiente incidente detectado en 2026 será INC-2026-0001.**

Las pruebas pueden consumir valores de secuencia aunque reviertan sus datos. Para volver a 0001 después de nuevas pruebas, usar el restablecimiento del simulador. El archivo queda separado y no aporta a las métricas actuales.

## Archivos cambiados en esta mejora

- aplicacion.py
- autenticacion.py
- modelos/__init__.py
- migraciones/003_archivo_academico.sql (nuevo)
- servicios/entorno_academico.py
- servicios/servicio_monitoreado.py
- plantillas/servicio_monitoreado.html
- plantillas/archivo_academico.html (nuevo)
- plantillas/base.html
- plantillas/simulador.html
- plantillas/historial.html
- plantillas/eventos.html
- plantillas/auditoria.html
- plantillas/macros.html
- estaticos/css/servicio_monitoreado.css (nuevo)
- estaticos/js/servicio_monitoreado.js (nuevo)
- estaticos/js/aplicacion.js
- pruebas/test_preview_reset.py (nuevo)
- pruebas/test_version_dos.py
- LEEME.md
- GUIA_EXPOSICION.md
- VERIFICACION.md
- evidencias/preview_reset_http.json (nuevo)

El reinicio de Waitress también actualizó sus archivos locales de ejecución: servidor.pid, servidor.log y servidor_error.log; se excluyen del código entregable.

## Pendiente de aceptación visual

La habilidad computer-use terminó la revisión porque no pudo determinar la URL del navegador con suficiente confianza. No se intentó eludir ese bloqueo. Por tanto, no se afirma validación visual de los breakpoints ni interacción manual real en navegador.

Revisar manualmente en 390, 768, 1024, 1366 y 1920 px, tanto claro como oscuro: legibilidad, ausencia de desbordamiento, ampliar/contraer/Escape, elegir entrada y cerrar feedback, acceso simulado, reacción a incidentes desde otra pestaña y retorno tras recuperación. La validación HTTP y de sintaxis no sustituye esa revisión visual.

No se detectaron regresiones en el alcance automatizado. Implementación funcional terminada; revisión visual humana pendiente antes de congelar/publicar. No se desplegó ni se contrataron servicios.

## Corrección UX final

- Bloqueo de simulación por componente afectado, incidente pendiente o contingencia; misma validación en backend y previsión. Latencia y caída web comparten componente y bloqueo.
- Acción única de Supervisor **Cerrar y normalizar servicio**, con restauración, desactivación de contingencia, cierre y auditoría.
- Ayuda SLA reducida a icono. Ritmo diferencia estado actual de SLA del período, incluso servicio operativo con SLA incumplido.
- La suite actual valida Flask sobre PostgreSQL real, roles, correlación, contingencia, resolución, cierre normalizado, trazabilidad y SLA.
- La correlación sigue probándose directamente con señales; no se alteraron umbrales, matriz, esquema ni datos persistentes del entorno durante estos casos (rollback). Las secuencias pueden avanzar al ejecutar la suite. El estado de numeración descrito anteriormente corresponde al reset de la ronda anterior.
- Sin despliegue. La aceptación visual manual registrada arriba continúa pendiente.

