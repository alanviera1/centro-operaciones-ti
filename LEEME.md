# CENTRO DE OPERACIONES TI v2.1

Centro de Operaciones de Servicios TI basado en prácticas de ITIL. Gestiona el servicio que soporta una plataforma de venta de entradas: no vende entradas ni procesa pagos.

**Propuesta:** convertir eventos técnicos en incidentes priorizados según su impacto sobre el servicio y el negocio. La infraestructura, las fallas, los usuarios afectados y las pérdidas son simulados. La autenticación, las reglas, PostgreSQL, las transacciones, la auditoría y los cálculos funcionan realmente. Se evolucionó el proyecto existente.

## Ejecutar

Requisitos comprobados: Python 3.11.9 y PostgreSQL 18.3 en localhost:5432. Flask, SQLAlchemy, psycopg, Flask-Login y Waitress; HTML/CSS/JavaScript/Jinja2 sin frameworks frontend ni CDN.

En PowerShell:

```powershell
cd C:\Users\Alan\Desktop\ITIL\escudo_ti
.\iniciar.ps1
```

Abrir **http://127.0.0.1:5055**. Si ya está funcionando, usar esa instancia, sin iniciar otra en el mismo puerto. Ctrl+C detiene una instancia iniciada en terminal. El script comprueba dependencias, prepara la base sin borrarla y ejecuta Waitress.

Alternativa con instalación preparada:

```powershell
..\.venv\Scripts\python.exe migrar_bd.py
..\.venv\Scripts\python.exe servidor_wsgi.py
```

La conexión local está en `.env`, archivo privado. Para una instalación nueva, copiar `.env.ejemplo` a `.env`, completar la conexión y generar un secreto con `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Guardarlo como SECRET_KEY. La variable anterior CLAVE_SESION sigue compatible.

## Acceso

No hay registro público. Cuentas creadas: **operador@escudoti.local** y **supervisor@escudoti.local**. Las contraseñas generadas están en **credenciales_locales.txt**, archivo privado de entrega excluido de Git. No publicarlo ni desplegarlo. PostgreSQL guarda únicamente hashes scrypt de Werkzeug.

| Capacidad | Operador | Supervisor |
|---|---|---|
| Consultar panel, eventos, incidentes e historial | Sí | Sí |
| Simular, iniciar atención, recuperar y resolver | Sí | Sí |
| Cerrar definitivamente | No | Sí |
| Restablecer entorno académico | No | Sí |
| Consultar auditoría | No | Sí |

Crear cuentas ausentes con `..\.venv\Scripts\python.exe crear_usuarios.py`. Solicita contraseñas sin mostrarlas (12–128 caracteres), o admite CLAVE_INICIAL_OPERADOR y CLAVE_INICIAL_SUPERVISOR en el entorno. Nunca modifica cuentas existentes. No se añadió gestión web de usuarios ni recuperación de contraseña.

Flask-Login identifica al usuario. Los permisos se validan en el servidor, además de mostrarse en la interfaz. Hay CSRF en POST, renovación de sesión al entrar, duración de ocho horas, cookies HttpOnly/SameSite=Lax y bloqueo de cinco minutos tras cinco fallos por cuenta. Producción exige secreto aleatorio de al menos 32 caracteres, cookie Secure y debug=False.

## Navegación e interfaz

- **Vista general:** estado del servicio, disponibilidad, SLA, usuarios afectados, recuperación, componentes y eventos recientes. “Incidentes por atender o cerrar” suma activos (abiertos/en proceso) y resueltos pendientes de cierre, mostrando ambos grupos por separado. No contiene formularios del simulador.
- **Incidentes:** abiertos, en proceso y resueltos pendientes de cierre; filtros por estado, prioridad, componente y código.
- **Registro de eventos:** señales del ciclo actual filtradas por nivel, componente y fecha de Lima.
- **Simulador — Laboratorio de eventos:** cinco escenarios uniformes: latencia, pagos, web, base de datos y autenticación.
- **Historial:** cerrados, recuperación, duración, responsable y acceso al historial de ciclos de demostración.
- **Auditoría:** accesos, simulaciones, acciones y restablecimientos; solo supervisor. Filtros combinables por acción, usuario (incluido sistema), referencia/código y fecha de Lima, con paginación.

Incidentes e historial muestran 12 filas por página; eventos 15; auditoría 20. La paginación conserva filtros. El detalle incluye impacto, urgencia, estimación económica, caída, SLA, matriz y línea de tiempo con responsables. Las acciones anteriores a v2 permanecen sin atribución conocida: no se inventaron usuarios históricos.

El botón ☀/☾ cambia el tema y guarda la preferencia en localStorage; inicialmente respeta el sistema. Hasta 800 px, las tablas principales se transforman en tarjetas y los campos secundarios quedan en el detalle. Se verificaron 390, 768, 1024, 1366 y 1920 px. Hay labels, foco visible, enlace para saltar al contenido, modales con Cancelar/Escape y toasts temporales. Se eliminaron el escudo E y los bordes azules decorativos.

## Reglas

Evento → correlación → impacto × urgencia → prioridad → incidente → recuperación → resolución → cierre.

Un evento crítico o tres advertencias del mismo componente en cinco minutos generan un incidente. Se consideran eventos sin atender, no archivados y aún sin incidente. Una advertencia aislada no implica un incidente. El índice parcial impide dos incidentes activos para un mismo componente; nuevos eventos se relacionan con el activo.

| Impacto / Urgencia | Baja (1) | Media (2) | Alta (3) |
|---|---|---|---|
| Bajo (1) | Baja | Baja | Media |
| Medio (2) | Baja | Media | Alta |
| Alto (3) | Media | Alta | Crítica |

Producto 1–2: baja; 3–4: media; 6: alta; 9: crítica. La matriz visible usa la misma función de la lógica. Pérdida estimada = operaciones fallidas × valor promedio de entrada (S/ 130 por defecto); no es un cobro.

Recuperar devuelve el servicio y termina la interrupción. Resolver verifica la recuperación. Tras resolver, el Supervisor dispone únicamente de **Cerrar y normalizar servicio**: restaura el principal si continúa caído, desactiva la contingencia y registra el cierre con trazabilidad.

**Disponibilidad = (tiempo acordado − tiempo caído) / tiempo acordado × 100.**

Período móvil: 43 200 minutos (período móvil de 30 días). Las interrupciones se recortan al período y se unen las simultáneas para evitar contar la misma caída dos veces. SLA cumplido si disponibilidad ≥ objetivo, incumplido si es menor. El margen no es negativo. “En riesgo” advierte consumo de al menos 80 % del presupuesto, sin convertir un SLA cumplido en incumplido.

Los minutos iniciales del simulador se agregan a la interrupción; por eso downtime puede superar el tiempo desde detección. Los históricos de demostración no archivados se incluyen explícitamente. Una caída antigua de varias horas conserva su duración: no se falsearon métricas.

Fechas almacenadas con zona horaria y generadas en UTC; presentación y filtros en America/Lima (UTC−5). El año visible del código corresponde a la fecha de detección en America/Lima, incluso alrededor de Año Nuevo. codigo_incidente usa una secuencia independiente de la PK. Ambas secuencias pueden saltar por rollback. El restablecimiento académico reinicia las secuencias operativas y la de códigos a 1 después de conservar el ciclo en archivo_academico. Todos los códigos usan INC-AAAA-NNNN, por ejemplo INC-2026-0001. La secuencia no se reinicia automáticamente por año. En cada ciclo operativo el código es único; en el archivo se identifica mediante ciclo + código. El formato fijo admite hasta 9999 valores; si se agota, la generación se detiene sin reutilizar códigos y se requiere ampliar el formato mediante otra migración.

## Restablecimiento académico

Supervisor → Simulador → **Restablecer entorno académico** → revisar advertencia → confirmar.

Copia eventos, incidentes, acciones, interrupciones y auditoría en **archivo_academico**, con los componentes y nombres/roles de los autores como contexto. Conserva sus estados y tiempos originales; un caso pendiente no se presenta como recuperado. Después vacía las cinco tablas operativas, reinicia sus secuencias y secuencia_codigo_incidente a 1, y restaura el servicio y todos sus componentes. Conserva usuarios, configuración, PK/FK y esquema. La auditoría actual comienza con una entrada ENTORNO_RESTABLECIDO, vinculada al ciclo archivado. Historial, Eventos y Auditoría permiten consultar el archivo por ciclos. Se rechaza cualquier incidente o evento no académico y una instalación con más de un servicio. Copia, vaciado y reinicio son una única transacción PostgreSQL: un fallo revierte todo. Los formularios anteriores al reset caducan para evitar acciones sobre identificadores reutilizados.

Las nuevas simulaciones inician otro conjunto de métricas. El primer incidente detectado en 2026 después del reset será **INC-2026-0001**, con PK 1. La PK y el código siguen teniendo secuencias independientes. El archivo conserva códigos repetidos entre ciclos sin colisionar con el ciclo activo. ENTORNO_ACADEMICO=false desactiva simulador y reset también en el servidor.

## Datos y migración

Respaldo original: `..\respaldo_pre_v2`, con código, .env privado, escudo_ti.dump, listado del dump, estado inicial y snapshot. No publicarlo. Se conservaron las columnas originales y los siete incidentes anteriores.

`migrar_bd.py` aplica `migraciones/001_version_dos.sql` de forma aditiva y transaccional. Usa bloqueo asesor PostgreSQL y `versiones_esquema` con huella SHA256. Repetirlo no duplica cambios y rechaza modificaciones de la migración aplicada. La migración 002_codigos_uniformes.sql normaliza los códigos existentes y las referencias exactas de auditoría, conservando PK, relaciones, acciones y tiempos. Comprueba unicidad y ancho antes de actualizar; falla sin cambios ante colisiones o números fuera de rango. La migración 003_archivo_academico.sql añade el archivo JSON por ciclos, sin cambiar las tablas ni FK existentes. El ejecutor aplica versiones ordenadas. Nunca editar una migración ya aplicada.

Se agregaron usuarios, auditoria, versiones_esquema; código único independiente, responsable y marcadores es_simulacion/archivado en incidentes; usuario en acciones; marcadores académicos en eventos; secuencia del código y FK hacia usuarios.

Las FK vinculan servicio → componentes → eventos/incidentes → acciones/interrupciones. Se conservan restricciones de estados, importes no negativos, fechas, campos obligatorios e incidente activo único; se agregan correo y código únicos. Usuarios nulos permiten acciones automáticas/anteriores a v2. auditoria.referencia es texto, no FK polimórfica. Auditoría no contiene contraseñas ni tokens.

preparar_bd.py es el instalador local: solo crea escudo_ti si falta. Producción usa otro preparador, sin crear bases ni incidentes históricos. Para restaurar un respaldo, detener escrituras y revisar con un administrador el destino; no restaurar destructivamente sobre la base activa para probarlo.

## Archivos principales

| Archivo | Responsabilidad |
|---|---|
| aplicacion.py, autenticacion.py | Rutas, sesión, permisos, CSRF, transacciones |
| modelos/__init__.py | Tablas, relaciones, restricciones, hashes |
| servicios/gestor_eventos.py, simulador.py | Generación y correlación |
| servicios/gestor_incidentes.py | Prioridad y ciclo del incidente |
| servicios/gestor_disponibilidad.py | Intervalos y métricas |
| servicios/entorno_academico.py, auditoria.py | Archivo y trazabilidad |
| plantillas/, estaticos/ | Interfaz, temas, responsive y modales |
| migrar_bd.py, migraciones/ | Evolución sin destruir datos |
| crear_usuarios.py | Alta inicial administrada |
| servidor_wsgi.py, preparar_produccion.py, render.yaml | Despliegue preparado |

## Pruebas

`..\.venv\Scripts\python.exe -m pytest pruebas -q`: **59 aprobadas** con PostgreSQL real. Los datos de prueba se revierten; las secuencias pueden avanzar. La instalación se prueba en un esquema temporal con rollback. No ejecutarlas contra producción con tráfico.

Consultar VERIFICACION.md, GUIA_EXPOSICION.md y DESPLIEGUE.md. consultas_demostracion.sql solo contiene lecturas para pgAdmin/psql.


## Pulido v2.1

La interfaz no muestra versión. Las cinco tarjetas conservan igual jerarquía; la última fila queda centrada. Respaldo adicional previo a esta ronda: ../respaldo_pre_v21, con código, dump y snapshot privados. Los resultados antiguos de generación se conservan en BD; la interfaz distingue sus conteos observados de la regla de correlación para no presentarlos como umbrales.

## Preparación final de exposición

El simulador consulta eventos elegibles y el incidente activo del componente para mostrar el resultado previsto. La previsión se actualiza cada diez segundos y el servidor valida nuevamente al ejecutar. Base de datos actualiza inmediatamente la prioridad al cambiar impacto/urgencia, usando la matriz enviada por el backend y conservando la mayor prioridad del incidente activo. Si el componente no está operativo, tiene un incidente pendiente de cierre o usa respaldo, su simulación queda bloqueada tanto en la interfaz como en el servidor. Se muestra su estado y el enlace al incidente cuando existe. Al cerrar y normalizar se habilita de nuevo. Latencia también queda bloqueada después de la primera advertencia; la correlación de señales sigue usando el umbral original, sin permitir repeticiones del simulador sobre un componente afectado.

Vista general incorpora ayuda contextual del SLA y el enlace **Ver servicio monitoreado**. La plataforma ficticia Ritmo Entradas muestra tres conciertos, pagos, autenticación y disponibilidad desde PostgreSQL. Compras e inicios simulados se validan también en el servidor; no generan cobros, reservas ni cuentas. La preview tiene identidad propia, banner, carteles, precios ficticios, vista ampliada y estados de web, pagos y autenticación. Consulta PostgreSQL cada cinco segundos y también al operar. La caída de pagos bloquea compra; autenticación bloquea acceso y compra; web sin respaldo pausa la plataforma; un respaldo activo muestra contingencia. Los mensajes de compra muestran un pase sin validez, y los fallos explican la causa. Una pérdida de conexión bloquea acciones hasta verificar el estado. Sin JavaScript, los formularios y recarga manual siguen funcionando. No altera la sesión del operador.

Para nuevas exposiciones se usa el restablecimiento de la interfaz, que conserva un ciclo separado antes de vaciar la operación y reiniciar la numeración.

Respaldo de esta limpieza: ../respaldo_exposicion_20260918_065842. Se restauró en una base temporal, se compararon todas las tablas y luego se retiró únicamente esa base temporal. El dump y su verificación permanecen privados.

## Mejora de preview y reset por ciclos (18/09/2026)

Respaldo previo privado: ../respaldo_preview_20260918_072318. Restauración real en una base temporal y comparación completa de las nueve tablas originales, con retirada de esa base temporal. La revisión visual mediante computer-use fue bloqueada por la herramienta al no poder confirmar la URL; pendiente inspección visual humana. No se realizó despliegue.

Ajuste UX final: el dashboard usa únicamente un icono de ayuda junto al SLA objetivo. Ritmo distingue estado actual del servicio y SLA del período: recuperar el servicio no elimina el downtime acumulado ni convierte un SLA incumplido en cumplido. Sin cambios de esquema, matriz o reglas de correlación.

