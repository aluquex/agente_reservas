# database.py
import psycopg2
from psycopg2.extras import RealDictCursor
import config

def _get_conn():
    return psycopg2.connect(host=config.DB_HOST, database=config.DB_NAME, user=config.DB_USER, password=config.DB_PASS)

def listar_servicios(negocio_id):
    with _get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id, nombre, precio FROM servicios WHERE negocio_id = %s ORDER BY id", (negocio_id,))
        return cur.fetchall()

def tiene_cita_futura(telefono, negocio_id):
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM reservas WHERE telefono = %s AND negocio_id = %s AND fecha >= CURRENT_DATE LIMIT 1", (telefono, negocio_id))
        return cur.fetchone() is not None

def obtener_horas_ocupadas(fecha, negocio_id):
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT hora FROM reservas WHERE fecha = %s AND negocio_id = %s", (fecha, negocio_id))
        return [item[0] for item in cur.fetchall()]

def obtener_citas_pasadas(telefono, negocio_id):
    with _get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT r.fecha, s.nombre as servicio_nombre FROM reservas r JOIN servicios s ON r.servicio_id = s.id WHERE r.telefono = %s AND r.negocio_id = %s AND r.fecha < CURRENT_DATE ORDER BY r.fecha DESC", (telefono, negocio_id))
        return cur.fetchall()

def obtener_citas_futuras_por_telefono(telefono, negocio_id):
    with _get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT r.id, r.fecha, r.hora, s.nombre as servicio_nombre FROM reservas r JOIN servicios s ON r.servicio_id = s.id WHERE r.telefono = %s AND r.negocio_id = %s AND r.fecha >= CURRENT_DATE ORDER BY r.fecha, r.hora", (telefono, negocio_id))
        return cur.fetchall()

def guardar_reserva(datos_reserva, negocio_id):
    # ... (código existente sin cambios)
    servicio_nombre = datos_reserva['servicio']
    servicio_id = None
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM servicios WHERE nombre = %s AND negocio_id = %s", (servicio_nombre, negocio_id))
        resultado = cur.fetchone()
        if resultado: servicio_id = resultado[0]
    if not servicio_id: raise ValueError(f"Servicio no encontrado")
    sql = "INSERT INTO reservas (nombre_cliente, telefono, servicio_id, fecha, hora, negocio_id) VALUES (%s, %s, %s, %s, %s, %s)"
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (datos_reserva['nombre'], datos_reserva['telefono'], servicio_id, datos_reserva['fecha'], datos_reserva['hora'], negocio_id))
    conn.commit()

def cancelar_cita(cita_id, negocio_id):
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM reservas WHERE id = %s AND negocio_id = %s", (cita_id, negocio_id))
        conn.commit()
        return cur.rowcount > 0

# --- NUEVA FUNCIÓN PARA MODIFICAR ---
def modificar_cita(cita_id, negocio_id, nuevos_datos):
    """
    Actualiza una cita existente.
    'nuevos_datos' es un diccionario con los campos a cambiar (ej: {"fecha": "2025-09-10"}).
    """
    # Primero, si se cambia el servicio, obtenemos su nuevo ID
    if 'servicio' in nuevos_datos:
        servicio_id = None
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM servicios WHERE nombre = %s AND negocio_id = %s", (nuevos_datos['servicio'], negocio_id))
            resultado = cur.fetchone()
            if resultado: servicio_id = resultado[0]
        if not servicio_id: raise ValueError(f"Servicio para modificar no encontrado")
        nuevos_datos['servicio_id'] = servicio_id
        del nuevos_datos['servicio'] # Eliminamos el nombre para no intentar actualizarlo

    # Construimos la consulta UPDATE dinámicamente
    campos_a_actualizar = ", ".join([f"{key} = %s" for key in nuevos_datos.keys()])
    valores = list(nuevos_datos.values())
    valores.append(cita_id)
    valores.append(negocio_id)
    
    sql = f"UPDATE reservas SET {campos_a_actualizar} WHERE id = %s AND negocio_id = %s"

    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, tuple(valores))
    conn.commit()