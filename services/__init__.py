"""
Servicio de conexión a PostgreSQL.
Provee un helper simple para obtener conexiones y ejecutar queries.
"""
import psycopg2
import psycopg2.extras
from config import Config


def get_connection():
    """Retorna una conexión activa a PostgreSQL."""
    return psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        dbname=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
    )


def query(sql, params=None, fetchone=False):
    """
    Ejecuta una consulta SELECT y retorna resultados como lista de diccionarios.
    Si fetchone=True, retorna solo un diccionario o None.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetchone:
                row = cur.fetchone()
                return dict(row) if row else None
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def execute(sql, params=None, returning=False):
    """
    Ejecuta una sentencia INSERT / UPDATE / DELETE.
    Si returning=True, retorna el primer resultado (útil para RETURNING id).
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            result = None
            if returning:
                row = cur.fetchone()
                result = dict(row) if row else None
            conn.commit()
            return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_transaction(operations):
    """
    Ejecuta múltiples operaciones dentro de una sola transacción.
    Recibe una lista de tuplas (sql, params).
    Si cualquiera falla, hace ROLLBACK total (todo-o-nada).
    Retorna lista de resultados (None para operaciones sin RETURNING).
    """
    conn = get_connection()
    results = []
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for sql, params in operations:
                cur.execute(sql, params)
                try:
                    row = cur.fetchone()
                    results.append(dict(row) if row else None)
                except psycopg2.ProgrammingError:
                    # No results to fetch (INSERT/UPDATE without RETURNING)
                    results.append(None)
            conn.commit()
            return results
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
