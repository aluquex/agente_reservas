# database.py
import psycopg2
from psycopg2.extras import RealDictCursor
import config

def _get_conn():
    return psycopg2.connect(host=config.DB_HOST, database=config.DB_NAME, user=config.DB_USER, password=config.DB_PASS)

def obtener_negocio_por_slug(slug):
    with _get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id, nombre FROM negocios WHERE slug = %s", (slug,))
        return cur.fetchone()

def obtener_horario_negocio(negocio_id):
    with _get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT horario_lunes, horario_martes, horario_miercoles, horario_jueves, 
                   horario_viernes, horario_sabado, horario_domingo 
            FROM negocios WHERE id = %s
        """, (negocio_id,))
        return cur.fetchone()

def listar_negocios(filtro_nombre=''):
    with _get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        if filtro_nombre:
            cur.execute("SELECT id, nombre, slug FROM negocios WHERE nombre ILIKE %s ORDER BY nombre", ('%' + filtro_nombre + '%',))
        else:
            cur.execute("SELECT id, nombre, slug FROM negocios ORDER BY nombre")
        return cur.fetchall()

def obtener_negocio_por_id(negocio_id):
    with _get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 1. Obtenemos todos los datos del negocio
        cur.execute("""
            SELECT id, nombre, slug, direccion, telefono, email,
                   horario_lunes, horario_martes, horario_miercoles,
                   horario_jueves, horario_viernes, horario_sabado, horario_domingo
            FROM negocios WHERE id = %s
        """, (negocio_id,))
        negocio = cur.fetchone()
        if not negocio:
            return None

        # 2. Servicios
        cur.execute("""
            SELECT nombre, precio, duracion_minutos
            FROM servicios WHERE negocio_id = %s
            ORDER BY id
        """, (negocio_id,))
        negocio['servicios'] = cur.fetchall()

        # 3. Empleados
        cur.execute("""
            SELECT nombre FROM empleados WHERE negocio_id = %s ORDER BY nombre
        """, (negocio_id,))
        negocio['empleados'] = cur.fetchall()

        return negocio

def crear_negocio_completo(datos):
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            sql_negocio = "INSERT INTO negocios (nombre, slug, direccion, telefono, email) VALUES (%s, %s, %s, %s, %s) RETURNING id"
            cur.execute(sql_negocio, (datos['nombre'], datos['slug'], datos['direccion'], datos['telefono'], datos['email']))
            negocio_id = cur.fetchone()[0]

            if datos['servicios']:
                sql_servicios = "INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (%s, %s, %s, %s)"
                servicios_a_insertar = [(negocio_id, s['nombre'], s['precio'], s['duracion']) for s in datos['servicios']]
                cur.executemany(sql_servicios, servicios_a_insertar)

            if datos['empleados']:
                sql_empleados = "INSERT INTO empleados (negocio_id, nombre) VALUES (%s, %s)"
                empleados_a_insertar = [(negocio_id, e['nombre']) for e in datos['empleados']]
                cur.executemany(sql_empleados, empleados_a_insertar)

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def modificar_negocio_completo(negocio_id, datos):
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            sql_update_negocio = """
            UPDATE negocios SET nombre = %s, slug = %s, direccion = %s, telefono = %s, email = %s,
            horario_lunes = %s, horario_martes = %s, horario_miercoles = %s, horario_jueves = %s,
            horario_viernes = %s, horario_sabado = %s, horario_domingo = %s WHERE id = %s
            """
            cur.execute(sql_update_negocio, (
                datos['nombre'], datos['slug'], datos['direccion'], datos['telefono'], datos['email'],
                datos['horario_lunes'], datos['horario_martes'], datos['horario_miercoles'],
                datos['horario_jueves'], datos['horario_viernes'], datos['horario_sabado'],
                datos['horario_domingo'], negocio_id
            ))

            cur.execute("DELETE FROM servicios WHERE negocio_id = %s", (negocio_id,))
            cur.execute("DELETE FROM empleados WHERE negocio_id = %s", (negocio_id,))

            if datos['servicios']:
                sql_servicios = "INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (%s, %s, %s, %s)"
                servicios_a_insertar = [(negocio_id, s['nombre'], s['precio'], s['duracion']) for s in datos['servicios']]
                cur.executemany(sql_servicios, servicios_a_insertar)

            if datos['empleados']:
                sql_empleados = "INSERT INTO empleados (negocio_id, nombre) VALUES (%s, %s)"
                empleados_a_insertar = [(negocio_id, e['nombre']) for e in datos['empleados']]
                cur.executemany(sql_empleados, empleados_a_insertar)

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def borrar_negocio(negocio_id):
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM reservas WHERE negocio_id = %s", (negocio_id,))
            cur.execute("DELETE FROM servicios WHERE negocio_id = %s", (negocio_id,))
            cur.execute("DELETE FROM empleados WHERE negocio_id = %s", (negocio_id,))
            cur.execute("DELETE FROM negocios WHERE id = %s", (negocio_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def listar_servicios(negocio_id):
    with _get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id, nombre, precio FROM servicios WHERE negocio_id = %s ORDER BY id", (negocio_id,))
        return cur.fetchall()

def listar_empleados(negocio_id):
    with _get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id, nombre FROM empleados WHERE negocio_id = %s AND activo = true ORDER BY nombre", (negocio_id,))
        return cur.fetchall()

def tiene_cita_futura(telefono, negocio_id):
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM reservas WHERE telefono = %s AND negocio_id = %s AND fecha >= CURRENT_DATE LIMIT 1", (telefono, negocio_id))
        return cur.fetchone() is not None

def obtener_horas_ocupadas(fecha, negocio_id, empleado_id):
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT TO_CHAR(hora, 'HH24:MI') as hora FROM reservas WHERE fecha = %s AND negocio_id = %s AND empleado_id = %s", (fecha, negocio_id, empleado_id))
        return [item[0] for item in cur.fetchall()]

def obtener_citas_pasadas(telefono, negocio_id):
    with _get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
        SELECT r.fecha, s.nombre as servicio_nombre
        FROM reservas r
        JOIN servicios s ON r.servicio_id = s.id
        WHERE r.telefono = %s AND r.negocio_id = %s AND r.fecha < CURRENT_DATE
        ORDER BY r.fecha DESC
        """, (telefono, negocio_id))
        return cur.fetchall()

def obtener_citas_futuras_por_telefono(telefono, negocio_id):
    with _get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
        SELECT r.id, r.fecha, r.hora, s.nombre as servicio_nombre, e.nombre as empleado_nombre
        FROM reservas r
        JOIN servicios s ON r.servicio_id = s.id
        JOIN empleados e ON r.empleado_id = e.id
        WHERE r.telefono = %s AND r.negocio_id = %s AND r.fecha >= CURRENT_DATE
        ORDER BY r.fecha, r.hora
        """, (telefono, negocio_id))
        return cur.fetchall()

def guardar_reserva(datos_reserva, negocio_id):
    servicio_nombre = datos_reserva['servicio']
    servicio_id = None
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM servicios WHERE nombre = %s AND negocio_id = %s", (servicio_nombre, negocio_id))
        resultado = cur.fetchone()
        if resultado:
            servicio_id = resultado[0]
    if not servicio_id:
        raise ValueError(f"Servicio no encontrado")
    sql = """
    INSERT INTO reservas (nombre_cliente, telefono, servicio_id, fecha, hora, negocio_id, empleado_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (
            datos_reserva['nombre'],
            datos_reserva['telefono'],
            servicio_id,
            datos_reserva['fecha'],
            datos_reserva['hora'],
            negocio_id,
            datos_reserva['empleado_id']
        ))
    conn.commit()

def cancelar_cita(cita_id, negocio_id):
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM reservas WHERE id = %s AND negocio_id = %s", (cita_id, negocio_id))
        conn.commit()
        return cur.rowcount > 0

def modificar_cita(cita_id, negocio_id, nuevos_datos):
    if 'servicio' in nuevos_datos:
        servicio_id = None
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM servicios WHERE nombre = %s AND negocio_id = %s", (nuevos_datos['servicio'], negocio_id))
            resultado = cur.fetchone()
            if resultado:
                servicio_id = resultado[0]
        if not servicio_id:
            raise ValueError(f"Servicio para modificar no encontrado")
        nuevos_datos['servicio_id'] = servicio_id
        del nuevos_datos['servicio']
    campos_a_actualizar = ", ".join([f"{key} = %s" for key in nuevos_datos.keys()])
    valores = list(nuevos_datos.values())
    valores.append(cita_id)
    valores.append(negocio_id)
    sql = f"UPDATE reservas SET {campos_a_actualizar} WHERE id = %s AND negocio_id = %s"
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, tuple(valores))
    conn.commit()
