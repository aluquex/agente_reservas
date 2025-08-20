# init_db.py
import psycopg2
import config

print("Iniciando la inicialización de la base de datos...")

try:
    # Usamos la configuración de config.py para conectar
    print(f"Conectando a la base de datos en: {config.DB_HOST}...")
    conn = psycopg2.connect(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        port=config.DB_PORT
    )
    cur = conn.cursor()
    print("Conexión exitosa.")

    print("Eliminando tablas antiguas si existen...")
    cur.execute("DROP TABLE IF EXISTS bloqueos CASCADE;")
    cur.execute("DROP TABLE IF EXISTS citas CASCADE;")
    cur.execute("DROP TABLE IF EXISTS servicios CASCADE;")
    cur.execute("DROP TABLE IF EXISTS empleados CASCADE;")
    cur.execute("DROP TABLE IF EXISTS negocios CASCADE;")
    print("Tablas eliminadas.")

    print("Creando la tabla 'negocios'...")
    cur.execute("""
        CREATE TABLE negocios (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(255) NOT NULL,
            slug VARCHAR(255) UNIQUE NOT NULL,
            direccion TEXT,
            telefono VARCHAR(20),
            email VARCHAR(255),
            horario_lunes TEXT,
            horario_martes TEXT,
            horario_miercoles TEXT,
            horario_jueves TEXT,
            horario_viernes TEXT,
            horario_sabado TEXT,
            horario_domingo TEXT
        );
    """)

    print("Creando la tabla 'servicios'...")
    cur.execute("""
        CREATE TABLE servicios (
            id SERIAL PRIMARY KEY,
            negocio_id INTEGER NOT NULL REFERENCES negocios(id) ON DELETE CASCADE,
            nombre VARCHAR(255) NOT NULL,
            precio NUMERIC(10, 2) NOT NULL,
            duracion INTEGER NOT NULL
        );
    """)

    print("Creando la tabla 'empleados'...")
    cur.execute("""
        CREATE TABLE empleados (
            id SERIAL PRIMARY KEY,
            negocio_id INTEGER NOT NULL REFERENCES negocios(id) ON DELETE CASCADE,
            nombre VARCHAR(255) NOT NULL
        );
    """)
    
    print("Creando la tabla 'citas'...")
    cur.execute("""
        CREATE TABLE citas (
            id SERIAL PRIMARY KEY,
            negocio_id INTEGER NOT NULL REFERENCES negocios(id) ON DELETE CASCADE,
            nombre_cliente VARCHAR(255) NOT NULL,
            telefono VARCHAR(20) NOT NULL,
            servicio_id INTEGER NOT NULL REFERENCES servicios(id),
            empleado_id INTEGER REFERENCES empleados(id),
            fecha DATE NOT NULL,
            hora TIME NOT NULL,
            UNIQUE(negocio_id, empleado_id, fecha, hora)
        );
    """)

    print("Creando la tabla 'bloqueos'...")
    cur.execute("""
        CREATE TABLE bloqueos (
            id SERIAL PRIMARY KEY,
            negocio_id INTEGER NOT NULL REFERENCES negocios(id) ON DELETE CASCADE,
            fecha DATE NOT NULL,
            hora TIME NOT NULL,
            empleado_id INTEGER REFERENCES empleados(id),
            UNIQUE(negocio_id, fecha, hora, empleado_id)
        );
    """)
    print("Todas las tablas han sido creadas con éxito.")

    print("Insertando datos de ejemplo...")
    cur.execute(
        "INSERT INTO negocios (nombre, slug, horario_viernes, horario_sabado) VALUES (%s, %s, %s, %s) RETURNING id;",
        ("Peluqueria Samuel T", "ST", "09:00,10:00,11:00,12:00,16:00,17:00,18:00", "09:00,10:00,11:00,12:00")
    )
    samuel_id = cur.fetchone()[0]
    cur.execute("INSERT INTO servicios (negocio_id, nombre, precio, duracion) VALUES (%s, %s, %s, %s);", (samuel_id, 'Corte Adulto', 15.00, 30))
    cur.execute("INSERT INTO servicios (negocio_id, nombre, precio, duracion) VALUES (%s, %s, %s, %s);", (samuel_id, 'Corte y Barba', 22.00, 45))
    cur.execute("INSERT INTO empleados (negocio_id, nombre) VALUES (%s, %s);", (samuel_id, 'Samuel'))
    cur.execute("INSERT INTO empleados (negocio_id, nombre) VALUES (%s, %s);", (samuel_id, 'Laura'))

    cur.execute(
        "INSERT INTO negocios (nombre, slug, horario_lunes, horario_martes) VALUES (%s, %s, %s, %s) RETURNING id;",
        ("DC Barber", "DCB", "10:00,11:00,12:00", "10:00,11:00,12:00,17:00,18:00")
    )
    dc_id = cur.fetchone()[0]
    cur.execute("INSERT INTO servicios (negocio_id, nombre, precio, duracion) VALUES (%s, %s, %s, %s);", (dc_id, 'Corte Premium', 20.00, 30))
    cur.execute("INSERT INTO servicios (negocio_id, nombre, precio, duracion) VALUES (%s, %s, %s, %s);", (dc_id, 'Arreglo de Barba', 10.00, 15))
    cur.execute("INSERT INTO empleados (negocio_id, nombre) VALUES (%s, %s);", (dc_id, 'Daniel'))

    cur.execute(
        "INSERT INTO negocios (nombre, slug, horario_lunes, horario_martes, horario_miercoles, horario_jueves, horario_viernes) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;",
        ("Peluquería SialWeb (Demo)", "demo", "09:00,10:00,11:00,12:00", "09:00,10:00,11:00,12:00", "09:00,10:00,11:00,12:00", "09:00,10:00,11:00,12:00", "09:00,10:00,11:00,12:00")
    )
    demo_id = cur.fetchone()[0]
    cur.execute("INSERT INTO servicios (negocio_id, nombre, precio, duracion) VALUES (%s, %s, %s, %s);", (demo_id, 'Corte de Demostración', 10.00, 20))
    cur.execute("INSERT INTO servicios (negocio_id, nombre, precio, duracion) VALUES (%s, %s, %s, %s);", (demo_id, 'Peinado de Exhibición', 15.00, 30))
    cur.execute("INSERT INTO empleados (negocio_id, nombre) VALUES (%s, %s);", (demo_id, 'Alex (IA)'))
    print("Datos de ejemplo insertados.")

    conn.commit()
    print("Cambios guardados en la base de datos.")

except Exception as e:
    print(f"Ha ocurrido un error: {e}")

finally:
    if 'cur' in locals() and cur:
        cur.close()
    if 'conn' in locals() and conn:
        conn.close()
    print("Conexión a la base de datos cerrada. Proceso finalizado.")