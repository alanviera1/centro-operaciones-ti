CREATE TABLE IF NOT EXISTS archivo_academico (
    id_archivo SERIAL PRIMARY KEY,
    id_servicio INTEGER NOT NULL REFERENCES servicios(id_servicio),
    id_usuario INTEGER REFERENCES usuarios(id_usuario),
    fecha_hora TIMESTAMPTZ NOT NULL,
    contenido JSON NOT NULL
);
