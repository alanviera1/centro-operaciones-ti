# Preparación de despliegue — CENTRO DE OPERACIONES TI v2.1

Estado: preparado localmente. **No se crearon cuentas, servicios remotos ni cargos.** Falta autorizar la publicación y comprobar el despliegue real por HTTPS.

## Opción preparada

Para exposición de bajo tráfico: **Render Web Service Free + PostgreSQL Neon Free**. Es una propuesta técnica, no un servicio contratado. Render sirve Flask por HTTPS; PostgreSQL remoto conserva las filas fuera del disco efímero.

Según fuentes oficiales consultadas el 18/09/2026, Render Free se suspende tras 15 minutos inactivo y ofrece 750 horas mensuales por espacio. Arrancar de nuevo puede tardar aproximadamente un minuto. Su PostgreSQL gratuito expira a los 30 días: no se eligió para conservar el proyecto. El propio proveedor reserva Free para pruebas/proyectos, no como garantía productiva. [Render Free](https://render.com/docs/free).

Neon Free publica 0,5 GB, 100 CU-horas mensuales y 5 GB de transferencia por proyecto; suspende cómputo tras cinco minutos inactivo. Es un punto de partida para esta demostración sujeto a cuotas y condiciones vigentes. [Planes oficiales](https://github.com/neondatabase/website/blob/main/content/docs/introduction/plans.md).

Para operación comercial continua se requieren disponibilidad y respaldos acordados; los planes pagados necesitan autorización. No introducir tarjeta ni activar consumo adicional. Si una cuenta existente tiene facturación, revisar límites antes de crear recursos: Free no elimina posibles cargos adicionales de la cuenta.

## Preparación técnica

- servidor_wsgi.py: Waitress, cuatro hilos, PORT del proveedor, logs a consola y host 0.0.0.0 en producción.
- preparar_produccion.py: exige DATABASE_URL, migra, crea servicio y componentes ausentes, crea usuarios ausentes. No crea bases ni históricos de ejemplo.
- render.yaml: Web Service plan free, secretos privados; no define PostgreSQL de pago.
- .python-version: rama 3.11; Render selecciona el parche disponible. [Configuración Python](https://render.com/docs/python-version).
- requirements.txt, .env.ejemplo y exclusiones de secretos en .gitignore.

| Variable | Configuración |
|---|---|
| ENTORNO | produccion |
| SECRET_KEY | Aleatoria y estable, ≥32 caracteres; generación privada de Render |
| DATABASE_URL | PostgreSQL remoto con sslmode=require; preferir conexión directa para migrar |
| CLAVE_INICIAL_OPERADOR | Nueva contraseña, 12–128 caracteres |
| CLAVE_INICIAL_SUPERVISOR | Otra contraseña; no reutilizar claves locales |
| ENTORNO_ACADEMICO | true para exposición; false deshabilita laboratorio/reset |
| PORT | Asignado por proveedor; local usa PUERTO=5055 |
| MINUTOS_PERIODO | 43200 por defecto |
| VALOR_PROMEDIO_ENTRADA | 130 por defecto |

Retirar claves iniciales del entorno tras crear las cuentas: el preparador no cambia usuarios existentes. No imprimir variables ni subir .env. Usar un usuario PostgreSQL dedicado, sin transportar la contraseña del postgres local.

## Pasos tras autorización

1. Crear/seleccionar recursos gratuitos, revisar cuotas y obtener conexión PostgreSQL TLS.
2. Preparar repositorio con el contenido de escudo_ti como raíz. Excluir .env, credenciales, logs, evidencias privadas y respaldos. Si el repo contiene ITIL, ajustar root directory a escudo_ti.
3. Para trasladar datos locales, acordar qué evidencia se publicará y crear un dump de la versión actual privado. Restaurar solo en destino vacío, comprobar conteos. El backup pre-v2 permanece privado.
4. Aplicar render.yaml y configurar secretos. Build: `pip install -r requirements.txt`.
5. Inicio: `python preparar_produccion.py && python servidor_wsgi.py`. Se prepara al iniciar porque Free no ofrece consola/one-off jobs. Migración con bloqueo e inicialización idempotente; mantener una instancia en este diseño sencillo.
6. Verificar /salud, login HTTPS, cookie Secure, roles, simulación y trazabilidad. Una BD nueva comienza sin históricos; una restaurada conserva sus datos.
7. Reiniciar remotamente y comprobar persistencia. Revisar arranque frío, cuotas y errores. Acordar respaldos privados; no tratar Free como estrategia de backup.

## Seguridad y límites

Producción impide debug y exige secreto largo, cookie Secure/HttpOnly/SameSite, CSRF, rol en servidor y CSP/HSTS. /salud no revela secretos; devuelve 503 si PostgreSQL falla. Logs de errores de BD registran clase de excepción, no conexión.

El bloqueo por cuenta no reemplaza protección contra tráfico distribuido del proveedor. No se implementaron MFA, recuperación de contraseña ni administración web de usuarios. Antes de manejar datos reales se deben acordar gestión de cuentas, monitorización, respaldos y disponibilidad contratada.

El SLA del panel corresponde al servicio simulado, no al uptime de Render/Neon. No existe un agente real que convierta una caída del hosting en incidente.


La preparación aplica todas las migraciones numeradas disponibles, incluida la conservación de ciclos anteriores. El año de los códigos usa America/Lima.

