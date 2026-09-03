"""
Servicio de numeración correlativa atómica para Fichas Técnicas.

Usa la tabla `contador_fichas` con SELECT ... FOR UPDATE para
garantizar que dos transacciones simultáneas nunca obtengan
el mismo número correlativo del año.
"""
import psycopg2.extras
from services import get_connection


def obtener_siguiente_correlativo(anio):
    """
    Retorna el siguiente número correlativo para el año dado.

    Ejecuta dentro de una transacción con bloqueo de fila:
    1. SELECT ... FOR UPDATE bloquea la fila del año.
    2. Incrementa último_numero en 1.
    3. Retorna el nuevo número.

    Si el año no existe en la tabla, lo crea con correlativo 1.

    Returns:
        int: El número correlativo asignado (ej: 181)
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Intentar bloquear la fila del año actual
            cur.execute(
                """
                SELECT ultimo_numero
                FROM contador_fichas
                WHERE anio = %s
                FOR UPDATE
                """,
                (anio,)
            )
            row = cur.fetchone()

            if row is None:
                # Año no existe, crear con correlativo 1
                cur.execute(
                    """
                    INSERT INTO contador_fichas (anio, ultimo_numero)
                    VALUES (%s, 1)
                    RETURNING ultimo_numero
                    """,
                    (anio,)
                )
                resultado = cur.fetchone()
                nuevo_numero = resultado['ultimo_numero']
            else:
                # Incrementar el contador
                nuevo_numero = row['ultimo_numero'] + 1
                cur.execute(
                    """
                    UPDATE contador_fichas
                    SET ultimo_numero = %s
                    WHERE anio = %s
                    """,
                    (nuevo_numero, anio)
                )

            conn.commit()
            return nuevo_numero
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def formatear_correlativo(numero, anio):
    """
    Formatea el correlativo en el formato oficial con mínimo 3 dígitos: 004-2026

    Args:
        numero: Número correlativo (int o str)
        anio: Año fiscal (int o str)

    Returns:
        str: Formato oficial (ej: "004-2026", "042-2026", "123-2026", "1234-2026")
    """
    if numero is None:
        return f"000-{anio}"
    num_str = str(numero).strip()
    if num_str.isdigit():
        num_str = num_str.zfill(3)
    return f"{num_str}-{anio}"
