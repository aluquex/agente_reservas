# database.py — versión multi-negocio (con normalización de fecha/hora para JSON)
import psycopg2
import psycopg2.extras
from datetime import datetime, date, time
import config

# ✅ mientras probamos: negocio por defecto (lo cambiaremos a slug)
NEGOCIO_ID_POR_DEFECTO = 1

def get_db_connection():
    """
    Crea una conexión a la base de datos PostgreSQL.
    Si tu DATABASE_URL ya incluye sslmode, no hace falta pasar sslmode aquí.
    """
    # Si Railway requiere SSL explícito y tu URL no lo lleva, usa:
    # return psycopg2.connect(config.DATABASE_URL, sslmode="require")
    return psycopg2.connect(config.DATABASE_URL)

# ---------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------
def _to_iso_date(fecha_ddmmyyyy: str) -> str:
    """
    Convierte 'dd/mm/YYYY' -> 'YYYY-mm-dd' (formato que espera Postgres DATE).
    """
    return datetime.strptime(fecha_ddmmyyyy, "%d/%m/%Y").strftime("%Y-%m-%d")

def _as_dict_rows(rows):
    return [dict(r) for r in rows] if rows else []

def _row_to_client_dict(row: dict) -> dict:
    """
    Normaliza tipos devueltos por Postgres para que sean JSON-serializables
    y consistentes con el formato mostrado al usuario.
    - fecha:    date/datetime -> 'dd/mm/YYYY'
    - hora:     time          -> 'HH:MM'
    """
    if row is None:
        return None
    d = dict(row)

    f = d.get("fecha")
    if isinstance(f, (date, datetime)):
        d["fecha"] = f.strftime("%d/%m/%Y")

    h = d.get("hora")
    if isinstance(h, time):
        d["hora"] = h.strftime("%H:%M")

    return d

# ---------------------------------------------------------------------
# Funciones de negocio
# ---------------------------------------------------------------------
def anadir_reserva(reserva_data: dict, negocio_id: int = NEGOCIO_ID_POR_DEFECTO):
    """
    Añade una nueva reserva a la base de datos en el negocio indicado.

    reserva_data requiere:
      - nombre (str)
      - telefono (str)
      - servicio (str)
      - fecha (str 'dd/mm/YYYY')
      - hora (str 'HH:MM')
      - estado (opcional, default 'pendiente')
      - notas  (opcional)
    Devuelve: id de la reserva creada, o None si hay conflicto de franja.
    """
    conn = get_db_connection()
    try:
        fecha_iso = _to_iso_date(reserva_data["fecha"])
        estado = reserva_data.get("estado", "pendiente")
        notas = reserva_data.get("notas")

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO reservas
                  (negocio_id, servicio, nombre_cliente, telefono, fecha, hora, estado, notas)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    negocio_id,
                    reserva_data["servicio"],
                    reserva_data["nombre"],
                    reserva_data["telefono"],
                    fecha_iso,
                    reserva_data["hora"],  # 'HH:MM' -> Postgres time
                    estado,
                    notas,
                ),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return new_id
    except psycopg2.IntegrityError:
        # Violación de UNIQUE (negocio_id, fecha, hora) = franja ocupada
        conn.rollback()
        return None
    finally:
        conn.close()

def actualizar_cita(id_cita: int, datos_nuevos: dict, negocio_id: int = NEGOCIO_ID_POR_DEFECTO) -> bool:
    """
    Actualiza una reserva (mismo negocio). Devuelve True si ok, False si conflicto de franja.
    datos_nuevos:
      - servicio, fecha('dd/mm/YYYY'), hora('HH:MM'), estado(opc), notas(opc)
    """
    conn = get_db_connection()
    try:
        fecha_iso = _to_iso_date(datos_nuevos["fecha"])
        estado = datos_nuevos.get("estado", "pendiente")
        notas = datos_nuevos.get("notas")

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE reservas
                   SET servicio = %s,
                       fecha    = %s,
                       hora     = %s,
                       estado   = %s,
                       notas    = %s
                 WHERE id = %s AND negocio_id = %s
                """,
                (
                    datos_nuevos["servicio"],
                    fecha_iso,
                    datos_nuevos["hora"],
                    estado,
                    notas,
                    id_cita,
                    negocio_id,
                ),
            )
        conn.commit()
        return True
    except psycopg2.IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()

def get_citas_por_telefono(telefono: str, negocio_id: int = NEGOCIO_ID_POR_DEFECTO):
    """
    Devuelve las citas de un teléfono dentro de un negocio.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT *
                  FROM reservas
                 WHERE telefono = %s AND negocio_id = %s
                 ORDER BY id DESC
                """,
                (telefono, negocio_id),
            )
            rows = cur.fetchall()
            # Normalizamos fecha/hora para JSON
            return [_row_to_client_dict(r) for r in rows]
    finally:
        conn.close()

def get_cita_por_id(id_cita: int, negocio_id: int = NEGOCIO_ID_POR_DEFECTO):
    """
    Devuelve una reserva por id (asegura pertenencia al negocio).
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM reservas WHERE id = %s AND negocio_id = %s",
                (id_cita, negocio_id),
            )
            row = cur.fetchone()
            # Normalizamos fecha/hora para JSON
            return _row_to_client_dict(row) if row else None
    finally:
        conn.close()

def cancelar_cita(id_cita: int, negocio_id: int = NEGOCIO_ID_POR_DEFECTO) -> bool:
    """
    Elimina una reserva del negocio. Devuelve True si borró algo.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM reservas WHERE id = %s AND negocio_id = %s",
                (id_cita, negocio_id),
            )
            deleted = cur.rowcount
        conn.commit()
        return deleted > 0
    finally:
        conn.close()

def cita_ya_existe(fecha_ddmmyyyy: str, hora_hhmm: str, negocio_id: int = NEGOCIO_ID_POR_DEFECTO) -> bool:
    """
    Comprueba si existe una reserva en esa franja para ese negocio.
    """
    conn = get_db_connection()
    try:
        fecha_iso = _to_iso_date(fecha_ddmmyyyy)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                  FROM reservas
                 WHERE fecha = %s AND hora = %s AND negocio_id = %s
                 LIMIT 1
                """,
                (fecha_iso, hora_hhmm, negocio_id),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()

# ---------------------------------------------------------------------
# Utilidades multi-negocio (para cuando pasemos a slug)
# ---------------------------------------------------------------------
def get_negocio_id_por_slug(slug: str):
    """
    Busca el id del negocio por su slug. Devuelve int o None.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM negocios WHERE slug = %s", (slug,))
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


