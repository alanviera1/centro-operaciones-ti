ALTER TABLE incidentes ADD COLUMN codigo_incidente VARCHAR(35);
ALTER TABLE incidentes ADD COLUMN es_simulacion BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE incidentes ADD COLUMN archivado BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE incidentes ADD COLUMN id_responsable INTEGER REFERENCES usuarios(id_usuario);
UPDATE incidentes SET codigo_incidente = 'INC-' || EXTRACT(YEAR FROM fecha_inicio)::TEXT || '-' ||
    to_char(nextval('secuencia_codigo_incidente'), 'FM000000');
ALTER TABLE incidentes ALTER COLUMN codigo_incidente SET NOT NULL;
ALTER TABLE incidentes ADD CONSTRAINT codigo_incidente_unico UNIQUE (codigo_incidente);
ALTER TABLE incidentes ALTER COLUMN es_simulacion SET DEFAULT FALSE;
ALTER TABLE eventos ADD COLUMN es_simulacion BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE eventos ADD COLUMN archivado BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE eventos ALTER COLUMN es_simulacion SET DEFAULT FALSE;
ALTER TABLE acciones_incidente ADD COLUMN id_usuario INTEGER REFERENCES usuarios(id_usuario);
