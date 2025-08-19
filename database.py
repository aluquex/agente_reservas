# database.py
import psycopg2
import psycopg2.extras
import config

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            port=config.DB_PORT
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error de conexión a la base de datos: {e}")
        raise

def obtener_negocio_por_slug(slug):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM negocios WHERE LOWER(slug) = %s;", (slug,))
            negocio = cur.fetchone()
            if negocio:
                negocio_id = negocio['id']
                cur.execute("SELECT nombre, precio FROM servicios WHERE negocio_id = %s;", (negocio_id,))
                servicios = cur.fetchall()
                cur.execute("SELECT id, nombre FROM empleados WHERE negocio_id = %s;", (negocio_id,))
                empleados = cur.fetchall()
                negocio = dict(negocio)
                negocio['servicios'] = [dict(s) for s in servicios]
                negocio['empleados'] = [dict(e) for e in empleados]
            return negocio
    finally:
        conn.close()

def obtener_negocio_por_id(negocio_id):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM negocios WHERE id = %s;", (negocio_id,))
            negocio = cur.fetchone()
            if negocio:
                cur.execute("SELECT nombre, precio FROM servicios WHERE negocio_id = %s;", (negocio_id,))
                servicios = cur.fetchall()
                cur.execute("SELECT id, nombre FROM empleados WHERE negocio_id = %s;", (negocio_id,))
                empleados = cur.fetchall()
                negocio = dict(negocio)
                negocio['servicios'] = [dict(s) for s in servicios]
                negocio['empleados'] = [dict(e) for e in empleados]
            return negocio
    finally:
        conn.close()

def listar_negocios(filtro_nombre=''):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            query = "SELECT id, nombre, slug FROM negocios ORDER BY nombre ASC"
            params = []
            if filtro_nombre:
                query = "SELECT id, nombre, slug FROM negocios WHERE nombre ILIKE %s ORDER BY nombre ASC;"
                params.append(f"%{filtro_nombre}%")
            cur.execute(query, params)
            return cur.fetchall()
    finally:
        conn.close()

def crear_negocio_completo(datos):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO negocios (nombre, slug, direccion, telefono, email) VALUES (%s, %s, %s, %s, %s) RETURNING id;",
                (datos['nombre'], datos['slug'], datos.get('direccion'), datos.get('telefono'), datos.get('email'))
            )
            negocio_id = cur.fetchone()[0]
            for servicio in datos['servicios']:
                cur.execute(
                    "INSERT INTO servicios (negocio_id, nombre, precio, duracion) VALUES (%s, %s, %s, %s);",
                    (negocio_id, servicio['nombre'], servicio['precio'], servicio['duracion'])
                )
            for empleado in datos['empleados']:
                cur.execute(
                    "INSERT INTO empleados (negocio_id, nombre) VALUES (%s, %s);",
                    (negocio_id, empleado['nombre'])
                )
            conn.commit()
    finally:
        conn.close()

def borrar_negocio(negocio_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM citas WHERE negocio_id = %s;", (negocio_id,))
            cur.execute("DELETE FROM servicios WHERE negocio_id = %s;", (negocio_id,))
            cur.execute("DELETE FROM empleados WHERE negocio_id = %s;", (negocio_id,))
            cur.execute("DELETE FROM negocios WHERE id = %s;", (negocio_id,))
            conn.commit()
    finally:
        conn.close()

def modificar_negocio_completo(negocio_id, datos):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE negocios SET 
                   nombre = %s, slug = %s, direccion = %s, telefono = %s, email = %s,
                   horario_lunes = %s, horario_martes = %s, horario_miercoles = %s,
                   horario_jueves = %s, horario_viernes = %s, horario_sabado = %s, horario_domingo = %s
                   WHERE id = %s;""",
                (datos['nombre'], datos['slug'], datos.get('direccion'), datos.get('telefono'), datos.get('email'),
                 datos.get('horario_lunes'), datos.get('horario_martes'), datos.get('horario_miercoles'),
                 datos.get('horario_jueves'), datos.get('horario_viernes'), datos.get('horario_sabado'),
                 datos.get('horario_domingo'), negocio_id)
            )
            cur.execute("DELETE FROM servicios WHERE negocio_id = %s;", (negocio_id,))
            for servicio in datos['servicios']:
                cur.execute(
                    "INSERT INTO servicios (negocio_id, nombre, precio, duracion) VALUES (%s, %s, %s, %s);",
                    (negocio_id, servicio['nombre'], servicio['precio'], servicio['duracion'])
                )
            cur.execute("DELETE FROM empleados WHERE negocio_id = %s;", (negocio_id,))
            for empleado in datos['empleados']:
                cur.execute(
                    "INSERT INTO empleados (negocio_id, nombre) VALUES (%s, %s);",
                    (negocio_id, empleado['nombre'])
                )
            conn.commit()
    finally:
        conn.close()

def tiene_cita_futura(telefono, negocio_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM citas WHERE telefono = %s AND negocio_id = %s AND fecha >= NOW()::date;",
                (telefono, negocio_id)
            )
            return cur.fetchone() is not None
    finally:
        conn.close()

def obtener_citas_pasadas(telefono, negocio_id):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """SELECT c.*, s.nombre as servicio_nombre 
                   FROM citas c JOIN servicios s ON c.servicio_id = s.id
                   WHERE c.telefono = %s AND c.negocio_id = %s AND c.fecha < NOW()::date 
                   ORDER BY c.fecha DESC LIMIT 1;""",
                (telefono, negocio_id)
            )
            return cur.fetchall()
    finally:
        conn.close()

def listar_servicios(negocio_id):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT id, nombre, precio FROM servicios WHERE negocio_id = %s;", (negocio_id,))
            return cur.fetchall()
    finally:
        conn.close()

def listar_empleados(negocio_id):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT id, nombre FROM empleados WHERE negocio_id = %s;", (negocio_id,))
            return cur.fetchall()
    finally:
        conn.close()

def obtener_horario_negocio(negocio_id):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                "SELECT horario_lunes, horario_martes, horario_miercoles, horario_jueves, horario_viernes, horario_sabado, horario_domingo FROM negocios WHERE id = %s;",
                (negocio_id,)
            )
            return cur.fetchone()
    finally:
        conn.close()

def obtener_horas_ocupadas(fecha_str, negocio_id, empleado_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            sql_citas = "SELECT TO_CHAR(hora, 'HH24:MI') FROM citas WHERE fecha = %s AND negocio_id = %s"
            params_citas = [fecha_str, negocio_id]
            if empleado_id:
                sql_citas += " AND empleado_id = %s"
                params_citas.append(empleado_id)
            sql_bloqueos = "SELECT TO_CHAR(hora, 'HH24:MI') FROM bloqueos WHERE fecha = %s AND negocio_id = %s"
            params_bloqueos = [fecha_str, negocio_id]
            if empleado_id:
                sql_bloqueos += " AND (empleado_id IS NULL OR empleado_id = %s)"
                params_bloqueos.append(empleado_id)
            else:
                sql_bloqueos += " AND (empleado_id IS NULL OR empleado_id IS NOT NULL)"
            final_sql = f"({sql_citas}) UNION ({sql_bloqueos});"
            cur.execute(final_sql, tuple(params_citas + params_bloqueos))
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()

def guardar_reserva(datos, negocio_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM servicios WHERE nombre = %s AND negocio_id = %s;",
                (datos['servicio'], negocio_id)
            )
            servicio_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO citas (negocio_id, nombre_cliente, telefono, servicio_id, fecha, hora, empleado_id) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s);""",
                (negocio_id, datos['nombre'], datos['telefono'], servicio_id, datos['fecha'], datos['hora'], datos.get('empleado_id'))
            )
            conn.commit()
    finally:
        conn.close()

def obtener_citas_futuras_por_telefono(telefono, negocio_id):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """SELECT c.id, c.fecha, c.hora, s.nombre as servicio_nombre, e.nombre as empleado_nombre
                   FROM citas c 
                   JOIN servicios s ON c.servicio_id = s.id
                   LEFT JOIN empleados e ON c.empleado_id = e.id
                   WHERE c.telefono = %s AND c.negocio_id = %s AND c.fecha >= NOW()::date;""",
                (telefono, negocio_id)
            )
            return cur.fetchall()
    finally:
        conn.close()

def cancelar_cita(cita_id, negocio_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM citas WHERE id = %s AND negocio_id = %s;", (cita_id, negocio_id))
            conn.commit()
    finally:
        conn.close()

def modificar_cita(cita_id, negocio_id, nuevos_datos):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if 'servicio' in nuevos_datos:
                cur.execute("SELECT id FROM servicios WHERE nombre = %s AND negocio_id = %s;", (nuevos_datos['servicio'], negocio_id))
                servicio_id = cur.fetchone()[0]
                cur.execute("UPDATE citas SET servicio_id = %s WHERE id = %s;", (servicio_id, cita_id))
            if 'fecha' in nuevos_datos and 'hora' in nuevos_datos:
                cur.execute("UPDATE citas SET fecha = %s, hora = %s WHERE id = %s;", (nuevos_datos['fecha'], nuevos_datos['hora'], cita_id))
            conn.commit()
    finally:
        conn.close()

def obtener_citas_para_exportar(negocio_id, fecha_inicio, fecha_fin):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            sql = """
                SELECT c.fecha, c.hora, c.nombre_cliente, c.telefono, s.nombre AS servicio_nombre, e.nombre AS empleado_nombre, s.precio
                FROM citas c JOIN servicios s ON c.servicio_id = s.id LEFT JOIN empleados e ON c.empleado_id = e.id
                WHERE c.negocio_id = %s AND c.fecha BETWEEN %s AND %s
                ORDER BY c.fecha, c.hora;
            """
            cur.execute(sql, (negocio_id, fecha_inicio, fecha_fin))
            return cur.fetchall()
    finally:
        conn.close()

def obtener_citas_del_dia(negocio_id, fecha):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            sql = """
                SELECT c.id, c.hora, c.nombre_cliente, c.telefono, s.nombre AS servicio_nombre, e.nombre AS empleado_nombre
                FROM citas AS c JOIN servicios AS s ON c.servicio_id = s.id LEFT JOIN empleados AS e ON c.empleado_id = e.id
                WHERE c.negocio_id = %s AND c.fecha = %s
                ORDER BY c.hora;
            """
            cur.execute(sql, (negocio_id, fecha))
            return cur.fetchall()
    finally:
        conn.close()

def cancelar_cita_cliente(cita_id, negocio_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM citas WHERE id = %s AND negocio_id = %s;", (cita_id, negocio_id))
            conn.commit()
    finally:
        conn.close()

def obtener_horas_bloqueadas(negocio_id, fecha):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            sql = "SELECT hora, empleado_id FROM bloqueos WHERE negocio_id = %s AND fecha = %s"
            cur.execute(sql, (negocio_id, fecha))
            return cur.fetchall()
    finally:
        conn.close()

def crear_bloqueo(negocio_id, fecha, hora, empleado_id=None):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            sql = "INSERT INTO bloqueos (negocio_id, fecha, hora, empleado_id) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING;"
            cur.execute(sql, (negocio_id, fecha, hora, empleado_id))
            conn.commit()
    finally:
        conn.close()

def eliminar_bloqueo(negocio_id, fecha, hora, empleado_id=None):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if empleado_id:
                sql = "DELETE FROM bloqueos WHERE negocio_id = %s AND fecha = %s AND hora = %s AND empleado_id = %s;"
                params = (negocio_id, fecha, hora, empleado_id)
            else:
                sql = "DELETE FROM bloqueos WHERE negocio_id = %s AND fecha = %s AND hora = %s AND empleado_id IS NULL;"
                params = (negocio_id, fecha, hora)
            cur.execute(sql, params)
            conn.commit()
    finally:
        conn.close()

def obtener_todas_las_citas(negocio_id):
    """
    Obtiene TODAS las citas de un negocio, sin filtro de fecha, para depuración.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            sql = """
                SELECT fecha, hora, nombre_cliente, telefono
                FROM citas WHERE negocio_id = %s ORDER BY fecha, hora;
            """
            cur.execute(sql, (negocio_id,))
            return cur.fetchall()
    finally:
        conn.close()