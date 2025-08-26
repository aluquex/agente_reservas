# init_db.py
import psycopg2
from psycopg2.extras import RealDictCursor
import os

DB_NAME = os.getenv("DB_NAME", "chatbot_sialweb_local")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))

def get_conn():
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )

def crear_tablas_basicas():
    with get_conn() as conn, conn.cursor() as cur:
        # --- EXISTENTES (resumen mínimo; conserva lo que ya tenías) ---
        cur.execute("""
        CREATE TABLE IF NOT EXISTS negocios (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            direccion TEXT,
            telefono TEXT,
            email TEXT,
            horario_lunes TEXT,
            horario_martes TEXT,
            horario_miercoles TEXT,
            horario_jueves TEXT,
            horario_viernes TEXT,
            horario_sabado TEXT,
            horario_domingo TEXT
        );""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS servicios (
            id SERIAL PRIMARY KEY,
            negocio_id INTEGER REFERENCES negocios(id) ON DELETE CASCADE,
            nombre TEXT NOT NULL,
            precio NUMERIC(10,2) DEFAULT 0,
            duracion_min INTEGER DEFAULT 30
        );""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
            id SERIAL PRIMARY KEY,
            negocio_id INTEGER REFERENCES negocios(id) ON DELETE CASCADE,
            nombre TEXT NOT NULL
        );""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS citas (
            id SERIAL PRIMARY KEY,
            negocio_id INTEGER REFERENCES negocios(id) ON DELETE CASCADE,
            nombre_cliente TEXT NOT NULL,
            telefono TEXT NOT NULL,
            servicio_id INTEGER REFERENCES servicios(id),
            empleado_id INTEGER REFERENCES empleados(id),
            fecha DATE NOT NULL,
            hora TIME NOT NULL
        );""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS bloqueos (
            id SERIAL PRIMARY KEY,
            negocio_id INTEGER REFERENCES negocios(id) ON DELETE CASCADE,
            fecha DATE NOT NULL,
            hora TIME NOT NULL,
            empleado_id INTEGER
        );""")

        # Ya implantada antes
        cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY,
            negocio_id INTEGER REFERENCES negocios(id) ON DELETE CASCADE,
            telefono TEXT NOT NULL,
            nombre TEXT,
            email TEXT,
            UNIQUE(negocio_id, telefono)
        );""")

        # --- NUEVA TABLA para no duplicar recordatorios ---
        cur.execute("""
        CREATE TABLE IF NOT EXISTS recordatorios_enviados (
            id SERIAL PRIMARY KEY,
            cita_id INTEGER NOT NULL REFERENCES citas(id) ON DELETE CASCADE,
            tipo TEXT NOT NULL,               -- '2h'
            enviado_en TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE (cita_id, tipo)
        );""")

        conn.commit()
        print("Tablas verificadas/creadas correctamente.")

if __name__ == "__main__":
    crear_tablas_basicas()
