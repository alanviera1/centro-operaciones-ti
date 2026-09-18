CREATE TEMP TABLE codigos_normalizados (
    id_incidente INTEGER PRIMARY KEY,
    anterior VARCHAR(35) NOT NULL UNIQUE,
    nuevo VARCHAR(35) NOT NULL UNIQUE CHECK (nuevo ~ '^INC-[0-9]{4}-[0-9]{4}$')
) ON COMMIT DROP;
INSERT INTO codigos_normalizados
SELECT id_incidente, codigo_incidente,
       'INC-' || EXTRACT(YEAR FROM fecha_inicio AT TIME ZONE 'America/Lima')::TEXT || '-' ||
       to_char(split_part(codigo_incidente, '-', 3)::BIGINT, 'FM0000')
FROM incidentes;
UPDATE incidentes SET codigo_incidente = 'MIGRACION-' || id_incidente;
UPDATE incidentes i SET codigo_incidente = c.nuevo
FROM codigos_normalizados c WHERE i.id_incidente = c.id_incidente;
UPDATE auditoria a SET referencia = c.nuevo
FROM codigos_normalizados c WHERE a.entidad = 'incidentes' AND a.referencia = c.anterior;
