# config.py
# =========================================
# Panel de control de nuestra aplicación.
# Contiene los ajustes esenciales para que el servidor funcione.
# =========================================

# --- Configuración de PostgreSQL ---

# La "dirección" de tu base de datos. 'localhost' significa que está en tu propia máquina.
DB_HOST = "localhost"

# El nombre de la base de datos a la que nos conectaremos.
DB_NAME = "chatbot_sialweb_local"

# El usuario con el que nos conectaremos. 'postgres' es el superusuario por defecto.
DB_USER = "postgres"

# La contraseña de tu usuario. ¡Asegúrate de que sea solo texto ASCII!
DB_PASS = "30980161Nn*" # <-- Confirma que esta sigue siendo tu contraseña correcta


# --- Configuración de Flask ---
SECRET_KEY = "mi-clave-secreta-para-el-chatbot"
FLASK_PORT = 5001


# --- Configuración de CORS ---
CORS_ALLOWED_ORIGINS = {
    "http://127.0.0.1:52370",
    "http://localhost:52370",
}