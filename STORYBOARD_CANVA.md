# Storyboard mínimo para Canva — próxima tarea

Este archivo prepara la futura creación de diapositivas; **no se diseñó ni publicó nada en Canva**. La presentación acompaña una sola demostración de 10 minutos. No reemplaza las pantallas de CENTRO DE OPERACIONES TI.

## Tres diapositivas sugeridas

| N.º | Título | Contenido mínimo | Presenta | Momento |
|---:|---|---|---|---|
| 1 | **ITIL en una sola vista** | **Usar el mapa general ya existente, sin rediseñarlo.** Centro «GESTIÓN DE SERVICIOS TI», subidea «Valor · Diseño · Seguridad · Transición» y sus cuatro bloques de sesiones 1–5. No convertirlo en mapa del proyecto. | Integrante 1 | 0:00–1:00; síntesis global, no lectura de 16 conceptos. |
| 2 | **Cuando falla un servicio digital** | Ritmo Entradas como ticketera ficticia de conciertos; una frase: caída del servidor web interrumpe la experiencia y exige atención trazable. Una imagen o esquema simple de servicio operativo → interrupción. | Integrante 2 | Aproximadamente 1:05–1:35. |
| 3 | **Cómo responde CENTRO DE OPERACIONES TI** | Cadena de una línea: evento → incidente/prioridad → Operador/recuperación → Supervisor/cierre → SLA/evidencia. Debajo, arquitectura mínima: Flask → servicios → modelos SQLAlchemy → PostgreSQL. | Integrante 2 | Aproximadamente 1:35–2:15. Al terminar, abandonar diapositivas. |

## Cambios de pantalla planificados

1. **Diapositivas → aplicación:** al terminar el Integrante 2, alrededor de 2:15, abrir Vista general con sesión Operador; el Integrante 3 inicia Ritmo Entradas y la falla.
2. **Aplicación → código:** el editor ya está abierto en una ventana preparada. La primera referencia breve es `aplicacion.py`/`crear_aplicacion` del Integrante 2 al presentar la arquitectura. Durante la demo se alterna solo cuando la función explica lo que acaba de verse: `simular_eventos` (3), `correlacionar_eventos` y `calcular_prioridad` (4), atención y recuperación (5), permiso y cierre (6), disponibilidad (7). Regresar de inmediato a la pantalla del incidente o del panel.
3. **Aplicación → PostgreSQL:** solo después del cierre, en la intervención del Integrante 7. Mostrar la consulta de lectura preparada en pgAdmin y comparar el código real con el del historial. No mostrar credenciales, hashes ni configuración privada.
4. **Cierre:** no volver a diapositivas. Concluir sobre el resultado visible y persistido: servicio normalizado, incidente cerrado y evidencia conservada.

## Reglas de diseño para la futura tarea

- Respetar literalmente el mapa existente **«ITIL en una sola vista»**. Sus cuatro bloques son **Fundamentos y estrategia**, **Diseño del servicio**, **Seguridad, continuidad y disponibilidad** y **Transición del servicio**. No añadir sesiones ni conceptos y no afirmar que CENTRO DE OPERACIONES TI implementa los 16 puntos.
- Mantener las diapositivas 2 y 3 sobrias: una idea principal cada una, poco texto y sin capturas llenas de tablas. Los detalles se muestran en la aplicación y el código.
- No usar diagramas que sugieran monitoreo externo o venta real: la infraestructura y la ticketera se simulan; los registros, reglas y PostgreSQL son reales.
- La cadena de gestión debe respetar el orden del flujo actual: **Detectado → En proceso → Servicio recuperado → Resuelto → Cerrado**. El cierre es **Cerrar y normalizar servicio**, exclusivo del Supervisor.

