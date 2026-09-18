# Checklist operativo — demo principal de CENTRO DE OPERACIONES TI

**Caso único:** caída del servidor web principal → respaldo web → resolución por Operador → cierre y normalización por Supervisor. **Duración de exposición:** 10 minutos, incluidos seis relevos breves. Esta guía prepara la ejecución; escribirla no restablece ni altera datos.

## A. Preparación previa, sin público

- [ ] Confirmar que la aplicación local responde en `http://127.0.0.1:5055`, que PostgreSQL responde y que el laboratorio académico está habilitado. Si la aplicación ya está abierta, usar esa instancia.
- [ ] Guardar el mapa existente **«ITIL en una sola vista»** como primera pantalla. No rediseñarlo. Preparar solo el apoyo mínimo de diapositivas indicado en `STORYBOARD_CANVA.md`.
- [ ] Tener a mano las credenciales de `operador@escudoti.local` y `supervisor@escudoti.local` **sin proyectar** contraseñas, `.env` ni `credenciales_locales.txt`.
- [ ] Revisar en Vista general y Simulador: `Servidor web principal` y `Servidor web de respaldo` operativos, escenario **Caída del servidor web** disponible, sin incidente activo de ese componente. Revisar la preview Ritmo Entradas.
- [ ] Para iniciar con métricas y caso limpios, el responsable de la preparación puede entrar como Supervisor y usar **Simulador → Restablecer entorno académico → confirmar**, **solo después de verificar** que hay un único servicio y datos exclusivamente académicos. El sistema guarda el ciclo anterior y vacía la operación en una transacción; no usarlo sobre datos ajenos ni durante la exposición. Luego cerrar sesión. Si no se cumple esa condición, no forzar el reset: preparar una instalación académica válida antes del día de la exposición.
- [ ] Volver a comprobar el estado inicial y entrar como **Operador**. Los formularios abiertos antes de un restablecimiento caducan: recargar todas las pestañas.
- [ ] Preparar pestañas: Vista general, Ritmo Entradas (`/servicio-monitoreado`), Simulador (`/simulador`) y Registro de eventos (`/eventos`). Dejar Historial (`/historial`) para el final. El detalle del incidente se abre al simular y su código se anota tal como aparezca.
- [ ] Preparar en el editor los bloques exactos: `aplicacion.py` → `crear_aplicacion` y `realizar_accion`; `servicios/simulador.py` → `ESCENARIOS['servidor']` y `simular_eventos`; `servicios/gestor_eventos.py` → `eventos_pendientes`, `correlacionar_eventos`; `servicios/gestor_incidentes.py` → `calcular_prioridad`, `acciones_disponibles`, `registrar_recuperacion`, `ejecutar_accion`; `autenticacion.py` → `exigir_supervisor`; `servicios/gestor_disponibilidad.py` → `calcular_disponibilidad`, `medir_servicio`.
- [ ] Dejar pgAdmin conectado a la **misma** base PostgreSQL. Abrir Query Tool con la consulta de lectura del apartado D, sin ejecutarla ni mostrar otras tablas hasta el Integrante 7.

**Estado observado al preparar estas guías (18/09/2026, solo lectura):** un servicio y seis componentes operativos; 25 incidentes cerrados, ningún activo ni resuelto pendiente; dos ciclos anteriores; ningún incidente/evento no simulado; disponibilidad del período `99,727 %`, caída `118,11 min`, SLA `INCUMPLIDO`. Estos datos pueden cambiar. Un restablecimiento previo válido evitaría presentar ese incumplimiento histórico como si lo causara el caso nuevo. No se ejecutó tal restablecimiento en esta tarea.

## B. Secuencia en vivo y resultado que habilita el siguiente paso

| Paso | Quién | Pantalla y clic exacto | Comprobar antes de seguir |
|---|---|---|---|
| 1 | 1 | Mostrar el mapa existente; **sin clics** | Se resumieron los cuatro bloques de sesiones 1–5, sin leer los 16 conceptos. |
| 2 | 2 | Vista general, sesión **Operador**. Señalar estado de servicio y **Ver servicio monitoreado**. | Ritmo Entradas funciona y el Operador está identificado. |
| 3 | 3 | Pulsar **Ver servicio monitoreado**. | Preview muestra «Servicio operativo» y web disponible. |
| 4 | 3 | Cambiar a Simulador. Buscar **Caída del servidor web**. Mantener **Caída inicial simulada (min) = 5**. Pulsar **Simular escenario →** una sola vez. | Redirección al detalle del nuevo incidente: estado visible **Detectado**, prioridad **Crítica**. Anotar su código real. |
| 5 | 3 | Cambiar a la pestaña de Ritmo y actualizar. Después abrir Registro de eventos. | Preview indica que el servidor web está caído; eventos «Servidor web no disponible» y «Conexiones HTTP fallidas», ambos críticos. |
| 6 | 4 | Desde uno de esos eventos, pulsar el código del incidente vinculado. | Mismo código para el componente web; matriz `3 × 3 = 9`, prioridad Crítica; solo **Iniciar atención**. |
| 7 | 5 | Pulsar **Iniciar atención**. | Estado **En proceso** y nombre del Operador como responsable; aparecen **Activar servidor de respaldo**, **Reiniciar servidor web** y **Escalar incidente**. No pulsar los dos últimos. |
| 8 | 5 | Pulsar **Activar servidor de respaldo** y confirmar el modal. | Estado visible **Servicio recuperado**; fecha de recuperación; principal `CAIDO`, respaldo `RESPALDO_ACTIVO`; la interrupción deja de crecer. |
| 9 | 5 | Actualizar Ritmo Entradas; volver al detalle. | Preview «Servicio operativo mediante contingencia»; acción y autor en línea de tiempo. |
| 10 | 5 | Pulsar **Marcar como resuelto** y confirmar. | Estado **Resuelto**; mensaje «Incidente resuelto. Pendiente de validación y cierre por supervisor.»; Operador no tiene botones de cierre ni acciones técnicas. **Aquí se cambia de rol.** |
| 11 | 6 | Pulsar **Salir**, entrar como `supervisor@escudoti.local`, abrir **Incidentes** y el código anotado. | Mismo caso **Resuelto**; única acción **Cerrar y normalizar servicio**. |
| 12 | 6 | Pulsar **Cerrar y normalizar servicio** y confirmar. | Estado **Cerrado**, fecha de cierre, servidor principal y respaldo operativos; línea de tiempo con restauración del principal, desactivación de contingencia y cierre. |
| 13 | 7 | Abrir Vista general → Historial → el caso → Auditoría → Historial → **Ciclos anteriores →**. | SLA/disponibilidad y caída visibles; caso cerrado con responsable/fechas; auditoría actual; ciclos anteriores separados de las métricas actuales. |
| 14 | 7 | Cambiar a pgAdmin y **ejecutar** la consulta de lectura preparada. | Último incidente en `incidentes` coincide en código, prioridad, estado `CERRADO` y fechas con la interfaz; `componentes` muestra principal y respaldo normalizados. |

### Reglas que no se deben improvisar

- Ejecutar **un solo escenario**. El de servidor web agrega dos eventos críticos; la regla de correlación requiere uno crítico **o** tres advertencias del mismo componente en cinco minutos. No crear otro incidente para explicarla.
- El valor `5` es caída inicial simulada. La caída total puede superar ligeramente cinco minutos mientras el caso está abierto; no prometer una cifra exacta de disponibilidad.
- `ABIERTO` es el estado interno que la interfaz muestra como **Detectado**. **Servicio recuperado** se muestra cuando el incidente sigue internamente `EN_PROCESO` y tiene `fecha_recuperacion`; después vienen `RESUELTO` y `CERRADO`.
- Activar el respaldo web recupera la experiencia mientras el principal continúa caído. **Cerrar y normalizar servicio** restaura el principal y desactiva el respaldo en la misma operación del Supervisor.
- No pulsar **Escalar incidente** en la ruta principal: es exclusivo del Operador y solo se puede registrar una vez; no recupera ni resuelve.
- No usar números de código memorizados ni contraseñas visibles. Si el escenario está bloqueado al iniciar, detener la demo y preparar el entorno antes de comenzar ante el profesor.

## C. Momento de las evidencias de código

El editor permanece listo, pero se abre solo al hablar de la acción que el público acaba de ver: Integrante 2, `crear_aplicacion` (arquitectura, unos segundos); Integrante 3, `ESCENARIOS['servidor']` y `simular_eventos` (señales); Integrante 4, `correlacionar_eventos` y `calcular_prioridad` (regla y matriz); Integrante 5, `acciones_disponibles`, `registrar_recuperacion` y ramas relevantes de `ejecutar_accion`; Integrante 6, `exigir_supervisor`, `realizar_accion` y rama `cerrar`; Integrante 7, `calcular_disponibilidad` y `medir_servicio`. Volver a la aplicación inmediatamente. El Integrante 1 mantiene solo el mapa.

## D. Consulta mínima para pgAdmin (solo lectura)

Seleccionar la base conectada a la aplicación. Ejecutar **al final**, después del cierre:

```sql
SELECT i.codigo_incidente, i.estado, i.prioridad,
       c.nombre AS componente, u.nombre AS responsable,
       i.fecha_recuperacion, i.fecha_resolucion, i.fecha_cierre
FROM incidentes AS i
JOIN componentes AS c ON c.id_componente = i.id_componente
LEFT JOIN usuarios AS u ON u.id_usuario = i.id_responsable
ORDER BY i.id_incidente DESC
LIMIT 1;

SELECT tipo, estado
FROM componentes
WHERE tipo IN ('WEB', 'WEB_RESPALDO')
ORDER BY tipo;
```

En la instalación preparada, un solo incidente nuevo hace que `ORDER BY ... DESC LIMIT 1` corresponda al código mostrado. Comparar ese código antes de interpretar la fila. Si no coincide, consultar por el código que aparece en la interfaz; **no editar datos**. `consultas_demostracion.sql` contiene más consultas de lectura, pero no hace falta proyectarlas todas.

## E. Si algo no coincide

- **Escenario bloqueado antes de iniciar:** hay componente no normalizado o incidente activo; no pulsar otras simulaciones. Preparar de nuevo fuera de la exposición.
- **Preview sigue mostrando estado previo:** actualizar la pestaña; la preview lee el estado guardado en PostgreSQL. No alterar filas manualmente.
- **SLA aparece incumplido:** explicar la caída acumulada del período y confirmar si hubo datos anteriores; no prometer que cerrar borra tiempo de caída.
- **No se puede cerrar:** comprobar que el mismo incidente está `RESUELTO` y que la sesión activa dice **Supervisor**. No manipular solicitudes.
- **pgAdmin muestra otro código:** está conectada a otra base o hubo otro incidente; seleccionar la conexión correcta y comparar el código anotado. No usar `UPDATE`, `DELETE`, `TRUNCATE` ni reset durante la demostración.

