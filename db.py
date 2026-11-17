import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

def get_database_url() -> str:
    """
    Obtiene la URL de la base de datos desde la variable de entorno DATABASE_URL.
    Render y otros servicios a menudo usan el esquema 'postgres://', el cual
    no es soportado directamente por psycopg2 y SQLAlchemy moderno.
    Esta función normaliza 'postgres://' a 'postgresql://'.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("La variable de entorno DATABASE_URL no está definida en el archivo .env o en el sistema.")
    
    # Compatibilidad con Render
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    return db_url

def get_connection():
    """
    Crea y retorna una nueva conexión a PostgreSQL.
    """
    url = get_database_url()
    return psycopg2.connect(url)

def init_db(schema_path: str = "schema.sql"):
    """
    Ejecuta el archivo schema.sql para crear tablas e insertar datos iniciales si no existen.
    Garantiza también la existencia de la columna 'notificado'.
    """
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"No se encontró el archivo de esquema: {schema_path}")
        
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
        
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
            # Asegurar columna notificado en tablas preexistentes
            cur.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS notificado BOOLEAN DEFAULT FALSE;")
        conn.commit()

# --- Operaciones de Tiendas ---

def obtener_tiendas():
    """Retorna la lista de tiendas registradas."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id_tienda, nombre, url_base FROM tiendas ORDER BY id_tienda ASC;")
            return cur.fetchall()

def obtener_o_crear_tienda(nombre: str, url_base: str = "") -> int:
    """Retorna el ID de la tienda existente o crea una nueva si no existe."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id_tienda FROM tiendas WHERE LOWER(nombre) = LOWER(%s);", (nombre.strip(),))
            row = cur.fetchone()
            if row:
                return row[0]
            
            cur.execute(
                "INSERT INTO tiendas (nombre, url_base) VALUES (%s, %s) RETURNING id_tienda;",
                (nombre.strip(), url_base.strip())
            )
            id_tienda = cur.fetchone()[0]
            conn.commit()
            return id_tienda

# --- Operaciones de Productos ---

def crear_producto(nombre: str, id_tienda: int, url_producto: str, precio_objetivo: float) -> int:
    """
    Registra un nuevo producto o actualiza su precio objetivo si ya existe la URL.
    Retorna el id_producto.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO productos (nombre, id_tienda, url_producto, precio_objetivo, notificado)
                VALUES (%s, %s, %s, %s, FALSE)
                ON CONFLICT (url_producto) 
                DO UPDATE SET 
                    nombre = EXCLUDED.nombre,
                    id_tienda = EXCLUDED.id_tienda,
                    precio_objetivo = EXCLUDED.precio_objetivo,
                    notificado = FALSE
                RETURNING id_producto;
                """,
                (nombre.strip(), id_tienda, url_producto.strip(), precio_objetivo)
            )
            id_producto = cur.fetchone()[0]
            conn.commit()
            return id_producto

def actualizar_estado_notificacion(id_producto: int, notificado: bool):
    """Actualiza si ya se envió la notificación de oferta para este producto."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE productos SET notificado = %s WHERE id_producto = %s;",
                (notificado, id_producto)
            )
            conn.commit()

def obtener_productos():
    """Retorna todos los productos con el nombre de su tienda asociada."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT 
                    p.id_producto, 
                    p.nombre, 
                    p.id_tienda, 
                    t.nombre AS tienda_nombre, 
                    p.url_producto, 
                    p.precio_objetivo,
                    p.notificado,
                    p.fecha_creacion
                FROM productos p
                LEFT JOIN tiendas t ON p.id_tienda = t.id_tienda
                ORDER BY p.id_producto DESC;
                """
            )
            return cur.fetchall()

def obtener_producto_por_id(id_producto: int):
    """Retorna la información detallada de un producto por su ID."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT 
                    p.id_producto, 
                    p.nombre, 
                    p.id_tienda, 
                    t.nombre AS tienda_nombre, 
                    p.url_producto, 
                    p.precio_objetivo,
                    p.notificado,
                    p.fecha_creacion
                FROM productos p
                LEFT JOIN tiendas t ON p.id_tienda = t.id_tienda
                WHERE p.id_producto = %s;
                """,
                (id_producto,)
            )
            return cur.fetchone()

def eliminar_producto(id_producto: int) -> bool:
    """Elimina un producto y en cascada su historial de precios."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM productos WHERE id_producto = %s;", (id_producto,))
            conn.commit()
            return cur.rowcount > 0

# --- Operaciones de Historial de Precios ---

def registrar_precio(id_producto: int, precio: float) -> int:
    """Registra una nueva lectura de precio para un producto."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO historial_precios (id_producto, precio)
                VALUES (%s, %s)
                RETURNING id_registro;
                """,
                (id_producto, precio)
            )
            nuevo_id = cur.fetchone()[0]
            conn.commit()
            return nuevo_id

def obtener_historial(id_producto: int):
    """Retorna el historial completo de precios ordenado cronológicamente para un producto."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id_registro, precio, fecha_registro
                FROM historial_precios
                WHERE id_producto = %s
                ORDER BY fecha_registro ASC;
                """,
                (id_producto,)
            )
            return cur.fetchall()

def obtener_resumen_productos():
    """
    Retorna una lista completa de productos para la tabla resumen:
    - id_producto, nombre, tienda, url_producto, precio_objetivo, notificado
    - precio_actual (último registrado)
    - precio_minimo (mínimo histórico)
    - fecha de última actualización
    - indicador de alerta (precio_actual <= precio_objetivo)
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                WITH ultimo_precio AS (
                    SELECT DISTINCT ON (id_producto)
                        id_producto,
                        precio AS precio_actual,
                        fecha_registro AS ultima_actualizacion
                    FROM historial_precios
                    ORDER BY id_producto, fecha_registro DESC
                ),
                minimo_historico AS (
                    SELECT 
                        id_producto, 
                        MIN(precio) AS precio_minimo
                    FROM historial_precios
                    GROUP BY id_producto
                )
                SELECT 
                    p.id_producto,
                    p.nombre,
                    COALESCE(t.nombre, 'Sin tienda') AS tienda,
                    p.url_producto,
                    p.precio_objetivo,
                    p.notificado,
                    up.precio_actual,
                    mh.precio_minimo,
                    up.ultima_actualizacion,
                    CASE 
                        WHEN up.precio_actual IS NOT NULL AND up.precio_actual <= p.precio_objetivo THEN TRUE
                        ELSE FALSE
                    END AS alerta_alcanzada
                FROM productos p
                LEFT JOIN tiendas t ON p.id_tienda = t.id_tienda
                LEFT JOIN ultimo_precio up ON p.id_producto = up.id_producto
                LEFT JOIN minimo_historico mh ON p.id_producto = mh.id_producto
                ORDER BY p.id_producto DESC;
                """
            )
            return cur.fetchall()
