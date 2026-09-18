# Guion maestro — CENTRO DE OPERACIONES TI

## Historia, tiempos y criterio de verdad

**Duración prevista: 10:00.** Intervenciones: 9:30; seis relevos de unos 5 segundos: 0:30. La exposición sigue un solo incidente: **Caída del servidor web**. El recorrido es mapa de sesiones 1–5 → problema de Ritmo Entradas → servicio operativo → falla → eventos → correlación y prioridad → atención del Operador → recuperación y resolución → cierre del Supervisor → SLA, trazabilidad y PostgreSQL.

CENTRO DE OPERACIONES TI es una aplicación Python/Flask con plantillas Jinja, servicios de lógica, modelos SQLAlchemy y persistencia PostgreSQL. La infraestructura y las operaciones de compra de Ritmo Entradas son simuladas; el registro, las transacciones, el cálculo, los permisos y la auditoría sí funcionan. Se aplica una regla propia de correlación y una matriz propia de prioridad inspiradas en la gestión de servicios; **ITIL no prescribe la fórmula exacta impacto × urgencia usada aquí**.

| Integrante | Parte | Tiempo |
|---|---|---:|
| 1 | Mapa general y puente al caso | 1:00 |
| 2 | Problema, caso y arquitectura | 1:10 |
| 3 | Servicio, falla y eventos | 1:20 |
| 4 | Correlación, incidente y prioridad | 1:20 |
| 5 | Operador, recuperación y resolución | 1:45 |
| 6 | Supervisor, cierre y normalización | 1:35 |
| 7 | SLA, historial, auditoría, PostgreSQL y conclusión | 1:20 |

### Preparación común, antes de que entre el profesor

No ejecutar el restablecimiento mientras se presenta. El responsable de la demo debe comprobar previamente que la instalación contiene solo datos académicos; entonces puede usar, como Supervisor, **Simulador → Restablecer entorno académico → confirmar**. La función conserva el ciclo anterior, vacía la operación y deja componentes operativos. Cerrar su sesión y entrar como **Operador** antes de iniciar. No proyectar `credenciales_locales.txt`, contraseñas ni `.env`.

**Estado inicial que debe verificarse, no suponerse:** `/` muestra servicio operativo; `WEB` y `WEB_RESPALDO` están `OPERATIVO`; `/simulador` muestra disponible **Caída del servidor web**; no hay incidente activo de `WEB`; `/servicio-monitoreado` muestra «Servicio operativo». Dejar **Caída inicial simulada (min)** en `5`. Confirmar que las cuentas `operador@escudoti.local` y `supervisor@escudoti.local` están activas y que PostgreSQL y la aplicación responden. En la revisión de solo lectura del 18/09/2026 había 25 incidentes cerrados y un SLA del período `INCUMPLIDO` por 118,11 minutos acumulados: **sin preparación previa no se debe prometer un SLA limpio**. No se hizo ningún restablecimiento para escribir estas guías.

Dejar preparados: (1) el mapa **«ITIL en una sola vista»** ya existente; (2) navegador en Vista general y una pestaña en `/servicio-monitoreado`; (3) pestaña en `/simulador`; (4) editor con `aplicacion.py`, `servicios/simulador.py`, `servicios/gestor_eventos.py`, `servicios/gestor_incidentes.py`, `autenticacion.py` y `servicios/gestor_disponibilidad.py` abiertos en los bloques indicados; (5) pgAdmin conectado a la base correcta, con la consulta de lectura de `GUIA_DEMO.md` preparada, **sin ejecutarla hasta el final**. Mantener el código de incidente que aparezca realmente en pantalla: no prometer `INC-…-0001` si la preparación no lo dejó así.

### Integrante 1 — Mapa general y conexión con el caso (1:00)

- **Pantalla:** el mapa existente **«ITIL en una sola vista»**. Centro: **GESTIÓN DE SERVICIOS TI**; subidea: **Valor · Diseño · Seguridad · Transición**. Señalar brevemente sus cuatro bloques: **Fundamentos y estrategia**, **Diseño del servicio**, **Seguridad, continuidad y disponibilidad**, **Transición del servicio**. El mapa contiene 16 conceptos de las sesiones 1–5; no leerlos uno por uno.
- **Guion oral:** «En las primeras cinco sesiones estudiamos el servicio TI desde cuatro perspectivas. En fundamentos entendimos qué es el servicio y cómo genera valor. En diseño vimos cómo hacerlo útil y gestionable para usuarios y proveedores. En seguridad, continuidad y disponibilidad analizamos cómo protegerlo y sostenerlo ante fallas. En transición vimos cómo introducir cambios controlados y conservar conocimiento sobre el servicio. El mapa reúne esas ideas; nuestro proyecto no implementa todos sus conceptos. Ahora vamos a aplicar una parte de ellos a una interrupción concreta».
- **Clics, en orden:** ninguno; mantener el mapa visible 50–60 segundos. **Resultado antes de continuar:** el público reconoce los cuatro bloques y entiende que el caso práctico viene después.
- **Concepto demostrado:** visión integral de la gestión del servicio, sin presentar el mapa como arquitectura de CENTRO DE OPERACIONES TI.
- **Código:** **ninguno en vivo**; abrir código aquí rompería la síntesis del mapa. Archivo de respaldo si el docente pregunta por el puente al software: `aplicacion.py`, función `crear_aplicacion`, que monta las rutas y conecta las capas. Recibe configuración y devuelve la aplicación Flask; sin ella no hay aplicación web. No explicar inicialización, sesiones ni tablas en este minuto.
- **Transición literal:** «Estos conceptos nos permiten entender un servicio TI desde su valor hasta su continuidad y transición. A partir de esa base desarrollamos un caso práctico donde analizamos qué ocurre cuando un servicio digital presenta una interrupción y cómo TI puede detectarla, atenderla, recuperarla y dejar evidencia de todo el proceso».

### Integrante 2 — Problema, caso y arquitectura (1:10)

- **Pantalla:** dejar el mapa y mostrar Vista general de CENTRO DE OPERACIONES TI; señalar **Ver servicio monitoreado**. Mostrar el esquema mínimo «Flask/rutas → servicios → modelos SQLAlchemy → PostgreSQL», sin una clase de arquitectura.
- **Guion oral:** «Ritmo Entradas representa una venta ficticia de entradas para conciertos de alta demanda. Si cae el servidor web, el usuario deja de acceder al servicio y el equipo TI necesita saber qué pasó, priorizar, recuperar y demostrar quién actuó. CENTRO DE OPERACIONES TI organiza ese trabajo: Flask recibe las acciones, los servicios aplican las reglas, SQLAlchemy guarda el estado en PostgreSQL y las vistas lo muestran. La ticketera es una preview académica conectada al mismo estado guardado».
- **Clics, en orden:** si el Operador aún no está conectado, entrar por `/login` con la cuenta de Operador; después abrir **Vista general**. No iniciar todavía la simulación. **Resultado:** rol Operador visible y servicio inicial operativo.
- **Concepto:** servicio TI y valor para el usuario; separación entre operación simulada y gestión persistente.
- **Código a enseñar durante unos 8 segundos:** `aplicacion.py`, función `crear_aplicacion`, concretamente registro del blueprint de autenticación e inicialización de `bd`. Recibe configuración, devuelve Flask y vincula rutas, sesión y BD. Si faltara, no habría punto de entrada común. No recorrer todas las rutas, cabeceras ni configuración de producción.
- **Transición:** «Ya tenemos el servicio y quién lo opera; veamos primero su estado normal y después qué señales aparecen cuando falla».

### Integrante 3 — Monitoreo y eventos (1:20)

- **Pantallas:** Vista general → **Ver servicio monitoreado** para ver Ritmo Entradas; luego `/simulador`; volver a la preview y abrir **Registro de eventos**. Señalar el mensaje de servicio normal, la tarjeta **Caída del servidor web**, el bloqueo visible tras la caída y las dos señales críticas.
- **Guion oral:** «Antes de la falla, Ritmo Entradas aparece disponible. Ahora simulamos una caída del servidor web principal con cinco minutos iniciales de interrupción. La vista del servicio deja de estar disponible y CENTRO DE OPERACIONES TI guarda dos eventos críticos: ‘Servidor web no disponible’ y ‘Conexiones HTTP fallidas’. Un evento es una señal observada; aún necesitamos decidir si exige gestionar un incidente».
- **Clics, en orden:** **Ver servicio monitoreado** → volver a `/simulador` → tarjeta **Caída del servidor web** → comprobar `5` minutos → **Simular escenario →** (el navegador abre el incidente) → cambiar a la pestaña de Ritmo y actualizar → **Registro de eventos**. **Resultado:** preview con servidor web caído, eventos críticos registrados y código de incidente creado. No pulsar **Elegir entrada** durante la caída; puede estar deshabilitado.
- **Concepto:** monitoreo mediante eventos y evidencia de una interrupción. Son eventos simulados, no agentes de infraestructura externa.
- **Código mínimo:** `servicios/simulador.py`, entrada `ESCENARIOS['servidor']` y el bucle que agrega `Evento` en `simular_eventos`. Recibe servicio, nombre de escenario y minutos; inserta señales, actualiza el componente y devuelve el incidente correlacionado. Sin ese bloque no habría señales persistentes para analizar. No leer los otros cuatro escenarios ni el HTML de Ritmo.
- **Transición:** «Las dos señales quedaron registradas. Ahora corresponde explicar por qué pertenecen a un mismo incidente y qué prioridad recibe».

### Integrante 4 — Correlación, incidente y prioridad (1:20)

- **Pantalla:** desde **Registro de eventos**, pulsar el código del incidente asociado a una señal. En el detalle señalar código real, componente `Servidor web principal`, eventos correlacionados, matriz y `3 × 3 = 9`, prioridad **Crítica**.
- **Guion oral:** «La regla del proyecto toma eventos del mismo componente, sin atender y dentro de cinco minutos. Un crítico basta, o tres advertencias. Este escenario genera dos críticos del servidor web; ambos quedan asociados a un solo incidente, no dos incidentes. El caso tiene impacto 3 y urgencia 3: nuestra matriz calcula 9 y lo clasifica como crítico. La multiplicación y los umbrales son decisiones explícitas de CENTRO DE OPERACIONES TI, no una fórmula obligatoria de ITIL».
- **Clics, en orden:** en un evento, pulsar el código del incidente; en el detalle no pulsar aún **Iniciar atención**. **Resultado:** incidente **Detectado**, única acción operativa visible **Iniciar atención**, matriz con prioridad crítica.
- **Concepto:** correlación de eventos, impacto, urgencia y priorización.
- **Código mínimo:** `servicios/gestor_eventos.py`, `eventos_pendientes` y principio de `correlacionar_eventos`; `servicios/gestor_incidentes.py`, `calcular_prioridad`. La primera recibe un componente y filtra señales; la segunda recibe componente, escenario, impacto, urgencia y minutos, vincula eventos y devuelve un incidente o `None`; la tercera recibe dos enteros 1–3 y devuelve BAJA/MEDIA/ALTA/CRITICA. Sin correlación no se crearían ni vincularían incidentes con esta regla; sin prioridad, la matriz no tendría la misma clasificación que la gestión. No explicar índices SQL, numeración ni pérdida económica.
- **Transición:** «La prioridad nos dice qué atender primero. El Operador toma ahora la responsabilidad y recupera el servicio».

### Integrante 5 — Operador, recuperación y resolución (1:45)

- **Pantalla:** detalle del incidente, con sesión **Operador**. Señalar «Responsable: Sin asignar», progreso de cinco etapas, acciones disponibles y línea de tiempo. Después de recuperar, mostrar brevemente la preview de Ritmo con contingencia y volver al detalle.
- **Guion oral:** «Al detectar el incidente no puedo saltar directamente a recuperarlo o cerrarlo. Pulso ‘Iniciar atención’: el estado pasa a En proceso y mi usuario queda responsable. Como falló el servidor web principal, elijo ‘Activar servidor de respaldo’, una acción técnica específica para ese componente. La plataforma vuelve mediante contingencia aunque el principal siga caído; se registra la recuperación y termina la interrupción. La línea de tiempo conserva cada acción y su autor. Finalmente marco el incidente como resuelto: ya está recuperado y verificado, pero yo no puedo cerrarlo. ‘Escalar incidente’ sería una opción del Operador una sola vez si hiciera falta apoyo; no la usamos en esta ruta principal».
- **Clics, en orden:** **Iniciar atención** → **Activar servidor de respaldo** → confirmar el modal → pestaña Ritmo, actualizar y mostrar «Servicio operativo mediante contingencia» → volver al detalle → **Marcar como resuelto** → confirmar. **Resultado:** primero **En proceso** con responsable; luego **Servicio recuperado**, `WEB` aún caído y respaldo activo; finalmente **Resuelto** con el aviso «Pendiente de validación y cierre por supervisor» y sin acciones técnicas ni cierre para Operador.
- **Concepto:** responsabilidad, recuperación mediante continuidad y separación entre recuperación, resolución y cierre.
- **Código mínimo:** `servicios/gestor_incidentes.py`, `acciones_disponibles`, ramas `iniciar` y `activar_respaldo` de `ejecutar_accion`, y `registrar_recuperacion`. La lista decide qué acciones admite el estado y el rol; `ejecutar_accion` recibe incidente y acción, modifica responsable, estado y componentes y registra la acción; `registrar_recuperacion` fija fecha, termina interrupción y marca eventos atendidos. Sin estas funciones podrían ofrecerse transiciones inválidas o perderse el momento de recuperación. No explicar el reinicio, el escalamiento ni todas las variantes de componente.
- **Transición:** «El servicio ya funciona y el Operador terminó su parte. El cierre requiere una validación diferente y normalizar la infraestructura».

### Integrante 6 — Supervisor, cierre y normalización (1:35)

- **Pantalla:** salir de la sesión de Operador, entrar como **Supervisor**, abrir **Incidentes** y el mismo código en estado **Resuelto**. Señalar que aparece una sola acción: **Cerrar y normalizar servicio**. Al finalizar mostrar los registros de restauración y desactivación de contingencia en la línea de tiempo.
- **Guion oral:** «El Supervisor comparte las acciones de atención y recuperación, pero además valida el cierre. En este estado solo dispone de ‘Cerrar y normalizar servicio’. El servidor principal todavía estaba caído mientras el respaldo daba continuidad. Esta operación restaura el principal, desactiva el respaldo, registra cada paso y marca el incidente cerrado con fecha. El Operador no podía enviarla ni manipulando la petición: el permiso se comprueba en el servidor».
- **Clics, en orden:** **Salir** → `/login` con Supervisor → **Incidentes** → abrir el código registrado → **Cerrar y normalizar servicio** → confirmar. **Resultado:** estado **Cerrado**, fecha de cierre, `WEB` y `WEB_RESPALDO` operativos, trazabilidad con acciones del Operador y Supervisor. No pulsar restablecimiento académico.
- **Concepto:** validación de rol, cierre administrativo, normalización y auditoría.
- **Código mínimo:** `autenticacion.py`, `exigir_supervisor`; `aplicacion.py`, ruta `realizar_accion`; `servicios/gestor_incidentes.py`, validación de `cerrar` y rama `cerrar` de `ejecutar_accion`. La ruta recibe identificador y acción, exige rol, llama al servicio y confirma la transacción; el servicio restaura principal, apaga contingencia, registra acciones y fecha. Sin la validación, un Operador podría cerrar; sin la rama de cierre, quedaría la contingencia activa o faltaría evidencia. No explicar CSRF, login interno ni todo el reset.
- **Transición:** «El caso está cerrado y normalizado. Revisemos qué muestran los indicadores y dónde queda guardada la evidencia».

### Integrante 7 — SLA, disponibilidad, historial, BD y conclusión (1:20)

- **Pantallas:** **Vista general** (20 s), **Historial** (12 s), **Auditoría** (10 s), **Historial → Ciclos anteriores** (8 s), pgAdmin ya preparado (20 s), conclusión (10 s). Señalar SLA objetivo, disponibilidad y caída acumulada sin prometer un número fijo; buscar el código real en Historial y su autor; en Auditoría señalar el cierre; en ciclos anteriores señalar que son evidencia separada y no afectan la métrica actual.
- **Guion oral:** «El SLA objetivo de este servicio es 99,90 %. La disponibilidad se calcula sobre el período móvil de 43 200 minutos y descuenta el tiempo de caída, contando una sola vez las interrupciones simultáneas. La recuperación detuvo la caída; el cierre no borra ese tiempo. En Historial vemos el caso cerrado con responsable y fechas, y en Auditoría las acciones asociadas. Los ‘Ciclos anteriores’ conservan evidencia de demostraciones restablecidas sin entrar en las métricas actuales. Por último, esta consulta en PostgreSQL muestra que el incidente y sus fechas quedaron persistidos. CENTRO DE OPERACIONES TI convierte una falla simulada en una gestión trazable y verificable».
- **Clics, en orden:** **Vista general** → **Historial** → abrir el mismo código si hace falta → **Auditoría** → volver a **Historial** → **Ciclos anteriores →** → cambiar a pgAdmin → ejecutar la consulta de lectura ya preparada. **Resultado:** registro `CERRADO` con prioridad, responsable y fechas, mismo código que en la interfaz; componentes normalizados. Si el SLA aparece `INCUMPLIDO`, explicar los períodos anteriores en vez de afirmar que la demo lo causó por sí sola.
- **Concepto:** disponibilidad, objetivo de servicio, trazabilidad y persistencia. El SLA es del servicio simulado, no del servidor de hosting.
- **Código mínimo:** `servicios/gestor_disponibilidad.py`, `calcular_disponibilidad` y `medir_servicio`. Reciben tiempos o el servicio, consultan interrupciones y devuelven porcentaje, caída, presupuesto y estado SLA; sin ellas el panel no podría sustentar su indicador. En pgAdmin enseñar `incidentes`, `componentes` y, si queda tiempo, `acciones_incidente`; la ruta `/historial` de `aplicacion.py` consulta los cerrados y `/auditoria` está reservada al Supervisor. No abrir hashes, migraciones, detalles de SQLAlchemy ni tablas ajenas al caso.
- **Conclusión:** «La infraestructura es ficticia para practicar con seguridad; la decisión, la recuperación, los permisos, las métricas y la evidencia son reales dentro del sistema».

## Código que cada estudiante debe poder defender

Al abrir un bloque, responder en una frase: **qué recibe, qué hace, qué cambia/devuelve, por qué existe y qué falla si se elimina**. El guion anterior asigna únicamente los bloques que sostienen la historia. No memorizar archivos completos. `modelos/__init__.py` sirve como apoyo: `Incidente` guarda prioridad, estado y fechas; `Evento` se vincula al incidente; `AccionIncidente` conserva acción/usuario; `Interrupcion` conserva la caída. El estado visible **Servicio recuperado** se deriva de `EN_PROCESO` más `fecha_recuperacion`; no requiere un valor adicional en la columna `estado`.

## POSIBLES PREGUNTAS DEL PROFESOR

| Pregunta | Respuesta breve |
|---|---|
| ¿Evento e incidente son lo mismo? | No. Un evento es una señal; la correlación decide si exige un incidente. |
| ¿Cuál es la regla de correlación? | Un crítico o tres advertencias del mismo componente en cinco minutos, sin atender, no archivados y aún sin incidente. |
| ¿Qué significan impacto y urgencia? | Son dos valores de 1 a 3 que el proyecto usa para clasificar el efecto y la necesidad de atención. |
| ¿ITIL exige multiplicarlos? | No. Impacto × urgencia y sus umbrales son reglas explícitas de CENTRO DE OPERACIONES TI. |
| ¿Qué es el SLA aquí? | El objetivo de disponibilidad del servicio simulado: 99,90 % en la configuración inicial. |
| ¿Cómo calculan disponibilidad? | `(minutos del período − minutos de caída) / minutos del período × 100`; se unen caídas simultáneas. |
| ¿Qué demuestra la contingencia? | El respaldo devuelve el servicio aunque el servidor principal siga caído; el cierre normaliza ambos. |
| ¿Qué diferencia al Operador del Supervisor? | Ambos atienden, recuperan y resuelven; solo Operador puede escalar y solo Supervisor puede cerrar y normalizar. |
| ¿Por qué PostgreSQL? | Guarda incidentes, eventos, acciones, fechas y usuarios con transacciones y relaciones reales. |
| ¿Qué conserva la trazabilidad? | La línea de tiempo, autor, resultado y fechas de cada acción; Auditoría registra operaciones del ciclo actual. |
| ¿Qué pasa si se elimina `registrar_recuperacion`? | Faltarían fecha de recuperación y fin de interrupción; la duración y la transición a resolución dejarían de ser coherentes. |
| ¿Por qué simular infraestructura si la gestión es real? | Permite provocar fallas repetibles sin afectar una ticketera real; Flask y PostgreSQL sí procesan y persisten la respuesta. |

