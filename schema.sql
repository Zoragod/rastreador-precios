-- =======================================================
-- Esquema de Base de Datos para Rastreador de Precios
-- Compatible con PostgreSQL Local y Render PostgreSQL
-- =======================================================

-- 1. Tabla de Tiendas
CREATE TABLE IF NOT EXISTS tiendas (
    id_tienda SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    url_base VARCHAR(255) NOT NULL DEFAULT '',
    fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabla de Productos
CREATE TABLE IF NOT EXISTS productos (
    id_producto SERIAL PRIMARY KEY,
    id_tienda INTEGER REFERENCES tiendas(id_tienda) ON DELETE CASCADE,
    nombre VARCHAR(200) NOT NULL,
    url_producto TEXT NOT NULL UNIQUE,
    precio_objetivo NUMERIC(10, 2) NOT NULL,
    notificado BOOLEAN DEFAULT FALSE,
    fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabla de Historial de Precios
CREATE TABLE IF NOT EXISTS historial_precios (
    id_registro SERIAL PRIMARY KEY,
    id_producto INTEGER REFERENCES productos(id_producto) ON DELETE CASCADE,
    precio NUMERIC(10, 2) NOT NULL,
    fecha_registro TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices para optimizar consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_productos_tienda ON productos(id_tienda);
CREATE INDEX IF NOT EXISTS idx_historial_producto_fecha ON historial_precios(id_producto, fecha_registro DESC);

-- Tiendas iniciales
INSERT INTO tiendas (nombre, url_base) VALUES 
('Books to Scrape', 'https://toscrape.com'),
('Steam', 'https://steampowered.com'),
('Otro', '')
ON CONFLICT (nombre) DO NOTHING;
