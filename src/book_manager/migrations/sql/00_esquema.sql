-- Esquema de Book Manager (Sprint 2)
-- Dialecto: sqlite
-- Generado por book_manager/migrations/migrations.py

CREATE TABLE generos (
	id INTEGER NOT NULL,
	nombre VARCHAR(80) NOT NULL,
	descripcion VARCHAR(200) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (nombre)
);

CREATE TABLE editoriales (
	id INTEGER NOT NULL,
	nombre VARCHAR(100) NOT NULL,
	pais VARCHAR(60) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (nombre)
);

CREATE TABLE monedas (
	id INTEGER NOT NULL,
	codigo VARCHAR(3) NOT NULL,
	nombre VARCHAR(60) NOT NULL,
	simbolo VARCHAR(10) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (codigo)
);

CREATE TABLE tipos_cotizacion (
	id INTEGER NOT NULL,
	nombre VARCHAR(60) NOT NULL,
	descripcion VARCHAR(200) NOT NULL,
	moneda_id INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_tipo_cotizacion_moneda_nombre UNIQUE (moneda_id, nombre),
	FOREIGN KEY(moneda_id) REFERENCES monedas (id)
);

CREATE TABLE libros (
	id INTEGER NOT NULL,
	isbn VARCHAR(13) NOT NULL,
	titulo VARCHAR(200) NOT NULL,
	autor VARCHAR(120) NOT NULL,
	editorial_id INTEGER NOT NULL,
	genero_id INTEGER NOT NULL,
	anio INTEGER NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (isbn),
	FOREIGN KEY(editorial_id) REFERENCES editoriales (id),
	FOREIGN KEY(genero_id) REFERENCES generos (id)
);

CREATE TABLE precios (
	id INTEGER NOT NULL,
	libro_id INTEGER NOT NULL,
	moneda_id INTEGER NOT NULL,
	valor NUMERIC(14, 2) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_precio_libro_moneda UNIQUE (libro_id, moneda_id),
	FOREIGN KEY(libro_id) REFERENCES libros (id) ON DELETE CASCADE,
	FOREIGN KEY(moneda_id) REFERENCES monedas (id)
);

CREATE TABLE stock (
	libro_id INTEGER NOT NULL,
	cantidad INTEGER NOT NULL,
	cantidad_minima INTEGER NOT NULL,
	PRIMARY KEY (libro_id),
	FOREIGN KEY(libro_id) REFERENCES libros (id) ON DELETE CASCADE
);

CREATE TABLE cotizaciones (
	tipo_id INTEGER NOT NULL,
	fecha DATE NOT NULL,
	compra NUMERIC(14, 2) NOT NULL,
	venta NUMERIC(14, 2) NOT NULL,
	PRIMARY KEY (tipo_id, fecha),
	FOREIGN KEY(tipo_id) REFERENCES tipos_cotizacion (id) ON DELETE CASCADE
);
