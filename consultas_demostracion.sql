-- Ejecutar en la base escudo_ti. Todas son consultas de lectura.
SELECT current_database() AS base_actual, version() AS version_postgresql;

SELECT nombre, sla_objetivo, estado FROM servicios;
SELECT nombre, tipo, estado FROM componentes ORDER BY id_componente;

SELECT id_incidente, codigo_incidente, titulo, impacto, urgencia, prioridad, estado,
       es_simulacion, archivado, id_responsable,
       usuarios_afectados, operaciones_fallidas, perdida_estimada,
       fecha_inicio, fecha_recuperacion, fecha_resolucion, fecha_cierre
FROM incidentes ORDER BY id_incidente DESC;

SELECT id_evento, id_incidente, tipo, nivel, descripcion, atendido
FROM eventos ORDER BY id_evento DESC;

SELECT i.codigo_incidente, a.accion, a.resultado,
       u.nombre AS usuario, u.rol, a.fecha_hora AT TIME ZONE 'America/Lima' AS fecha_lima
FROM acciones_incidente a
JOIN incidentes i ON i.id_incidente = a.id_incidente
LEFT JOIN usuarios u ON u.id_usuario = a.id_usuario
ORDER BY a.id_accion DESC;

SELECT id_incidente, minutos_caida, fecha_inicio, fecha_fin
FROM interrupciones ORDER BY id_interrupcion DESC;

SELECT id_usuario, nombre, correo, rol, activo FROM usuarios;
SELECT accion, entidad, referencia, id_usuario,
       fecha_hora AT TIME ZONE 'America/Lima' AS fecha_lima
FROM auditoria ORDER BY id_auditoria DESC;
SELECT version, fecha_hora FROM versiones_esquema;
