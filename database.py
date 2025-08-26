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

# -------------------------
# NEGOCIOS / SERVICIOS / EMPLEADOS
# -------------------------

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
                cur.execute("SELECT nombre, precio, duracion FROM servicios WHERE negocio_id = %s;", (negocio_id,))
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
            # Reset de datos dependientes
            cur.execute("DELETE FROM citas WHERE negocio_id = %s;", (negocio_id,))
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

# -------------------------
# CLIENTES (NUEVO)
# -------------------------

def upsert_cliente(negocio_id, telefono, email, nombre=None):
    """
    Crea o actualiza un cliente (por negocio + teléfono).
    Requiere email (la columna es NOT NULL).
    """
    if not (negocio_id and telefono and email):
        return
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO clientes (negocio_id, telefono, email, nombre)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (negocio_id, telefono)
                DO UPDATE SET
                    email = EXCLUDED.email,
                    nombre = COALESCE(EXCLUDED.nombre, clientes.nombre),
                    updated_at = NOW();
                """,
                (negocio_id, telefono, email, nombre)
            )
            conn.commit()
    finally:
        conn.close()

def obtener_email_cliente(telefono, negocio_id):
    """
    Devuelve el email guardado para un teléfono en un negocio, o None.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT email FROM clientes WHERE negocio_id = %s AND telefono = %s LIMIT 1;",
                (negocio_id, telefono)
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()

# -------------------------
# CITAS / DISPONIBILIDAD
# -------------------------

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
    """
    Inserta la cita y, si viene 'email' en datos, realiza upsert en clientes.
    datos = {
        'nombre', 'telefono', 'servicio', 'fecha', 'hora', 'empleado_id',  # (oblig/opt)
        'email' (opcional, para persistir cliente)
    }
    """
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
            # --- NUEVO: persistir cliente si se pasó email ---
            email = datos.get('email')
            if email:
                upsert_cliente(negocio_id, datos['telefono'], email, datos.get('nombre'))
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

# -------------------------
# DETALLES DE CITA (para emails)
# -------------------------

def obtener_cita_detalle(cita_id):
    """Devuelve un dict con detalles completos de la cita (incluye email del negocio)."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT 
                    c.id, c.negocio_id, c.nombre_cliente, c.telefono, c.fecha, c.hora,
                    c.servicio_id, s.nombre AS servicio_nombre,
                    c.empleado_id, e.nombre AS empleado_nombre,
                    n.email AS negocio_email, n.nombre AS negocio_nombre
                FROM citas c
                JOIN servicios s ON c.servicio_id = s.id
                LEFT JOIN empleados e ON c.empleado_id = e.id
                JOIN negocios n ON n.id = c.negocio_id
                WHERE c.id = %s
                """,
                (cita_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()

def obtener_email_negocio(negocio_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM negocios WHERE id = %s;", (negocio_id,))
            r = cur.fetchone()
            return r[0] if r else None
    finally:
        conn.close()

def cancelar_cita(cita_id, negocio_id):
    """
    Cancela una cita y devuelve sus detalles previos para email de notificación.
    Si no existe, devuelve None.
    """
    detalle = obtener_cita_detalle(cita_id)
    if not detalle or detalle.get('negocio_id') != negocio_id:
        return None

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM citas WHERE id = %s AND negocio_id = %s;", (cita_id, negocio_id))
            conn.commit()
    finally:
        conn.close()
    return detalle

def modificar_cita(cita_id, negocio_id, nuevos_datos):
    """
    Modifica una cita. Devuelve (antes, despues) como dicts para email.
    """
    antes = obtener_cita_detalle(cita_id)
    if not antes or antes.get('negocio_id') != negocio_id:
        return None, None

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if 'servicio' in nuevos_datos:
                cur.execute("SELECT id FROM servicios WHERE nombre = %s AND negocio_id = %s;", (nuevos_datos['servicio'], negocio_id))
                servicio_row = cur.fetchone()
                if servicio_row:
                    servicio_id = servicio_row[0]
                    cur.execute("UPDATE citas SET servicio_id = %s WHERE id = %s;", (servicio_id, cita_id))
            if 'fecha' in nuevos_datos and 'hora' in nuevos_datos:
                cur.execute("UPDATE citas SET fecha = %s, hora = %s WHERE id = %s;", (nuevos_datos['fecha'], nuevos_datos['hora'], cita_id))
        conn.commit()
    finally:
        conn.close()

    despues = obtener_cita_detalle(cita_id)
    return antes, despues

# -------------------------
# EXPORT / AGENDA / BLOQUEOS
# -------------------------

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
                SELECT 
                    c.id, c.hora, c.nombre_cliente, c.telefono, s.nombre AS servicio_nombre, e.nombre AS empleado_nombre
                FROM citas c JOIN servicios s ON c.servicio_id = s.id LEFT JOIN empleados e ON c.empleado_id = e.id
                WHERE c.negocio_id = %s AND c.fecha = %s
                ORDER BY c.hora;
            """
            cur.execute(sql, (negocio_id, fecha))
            return cur.fetchall()
    finally:
        conn.close()

def cancelar_cita_cliente(cita_id, negocio_id):
    # Mantener función existente, pero devolviendo el detalle previo para consistencia
    return cancelar_cita(cita_id, negocio_id)

def obtener_todas_las_citas(negocio_id):
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

# -------------------------
# RECURRENTE (última cita pasada)
# -------------------------

def obtener_ultima_cita_pasada(telefono, negocio_id):
    """
    Devuelve la última cita pasada del teléfono dado (dict con joins y email del negocio).
    Útil para saludo de usuario recurrente.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT 
                    c.id, c.negocio_id, c.nombre_cliente, c.telefono, c.fecha, c.hora,
                    c.servicio_id, s.nombre AS servicio_nombre,
                    c.empleado_id, e.nombre AS empleado_nombre,
                    n.email AS negocio_email, n.nombre AS negocio_nombre
                FROM citas c
                JOIN servicios s ON c.servicio_id = s.id
                LEFT JOIN empleados e ON c.empleado_id = e.id
                JOIN negocios n ON n.id = c.negocio_id
                WHERE c.telefono = %s AND c.negocio_id = %s AND c.fecha < NOW()::date
                ORDER BY c.fecha DESC
                LIMIT 1;
                """,
                (telefono, negocio_id)
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()

# ===================================================
# RECORDATORIOS 2h ANTES (NUEVO)
# ===================================================

def ensure_tabla_recordatorios():
    """
    Crea la tabla de control de recordatorios si no existe.
    Evita enviar múltiples veces el mismo recordatorio por cita y tipo.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS recordatorios_enviados (
                    id SERIAL PRIMARY KEY,
                    cita_id INTEGER NOT NULL,
                    tipo VARCHAR(20) NOT NULL,
                    enviado_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    UNIQUE (cita_id, tipo)
                );
            """)
            conn.commit()
    finally:
        conn.close()

def obtener_citas_para_recordatorio_2h(desde_dt, hasta_dt):
    """
    Devuelve citas cuyo (fecha + hora) esté entre [desde_dt, hasta_dt)
    y que aún no tengan recordatorio '2h' enviado.
    Incluye datos de negocio/servicio/empleado y email del cliente (si existe).
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT c.id, c.negocio_id, c.fecha, c.hora, c.nombre_cliente, c.telefono,
                       s.nombre AS servicio_nombre,
                       e.nombre AS empleado_nombre,
                       n.nombre AS negocio_nombre, n.slug AS negocio_slug, n.email AS negocio_email, n.direccion,
                       cli.email AS cliente_email
                FROM citas c
                JOIN negocios n ON n.id = c.negocio_id
                LEFT JOIN servicios s ON s.id = c.servicio_id
                LEFT JOIN empleados e ON e.id = c.empleado_id
                LEFT JOIN clientes  cli ON cli.negocio_id = c.negocio_id AND cli.telefono = c.telefono
                WHERE (c.fecha + c.hora BETWEEN %s AND %s)
                  AND NOT EXISTS (
                        SELECT 1 FROM recordatorios_enviados r
                        WHERE r.cita_id = c.id AND r.tipo = '2h'
                  )
                ORDER BY c.fecha, c.hora, c.id;
            """, (desde_dt, hasta_dt))
            return cur.fetchall()
    finally:
        conn.close()

def marcar_recordatorio_enviado(cita_id, tipo="2h"):
    """
    Marca un recordatorio como enviado para una cita (no se repetirá).
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO recordatorios_enviados (cita_id, tipo) VALUES (%s, %s)
                ON CONFLICT (cita_id, tipo) DO NOTHING;
            """, (cita_id, tipo))
            conn.commit()
    finally:
        conn.close()
