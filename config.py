# config.py
import os

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "30980161Nn*")

# --- LÓGICA ROBUSTA PARA LEER LAS VARIABLES DE RAILWAY ---
# Leemos las variables de la URL de conexión que Railway sí proporciona de forma fiable
database_url = os.getenv("DATABASE_URL")

if database_url:
    # Si estamos en producción, parseamos la URL
    from urllib.parse import urlparse
    result = urlparse(database_url)
    DB_USER = result.username
    DB_PASSWORD = result.password
    DB_HOST = result.hostname
    DB_PORT = result.port
    DB_NAME = result.path[1:] # Quitamos la barra inicial '/'
else:
    # Si estamos en local, usamos nuestros valores por defecto
    DB_HOST = "localhost"
    DB_NAME = "chatbot_sialweb_local"
    DB_USER = "postgres"
    DB_PASSWORD = "30980161Nn*"
    DB_PORT = 5432

# La SECRET_KEY es vital para la seguridad de las sesiones en producción
SECRET_KEY = os.getenv("SECRET_KEY", "una-clave-secreta-muy-larga-y-dificil-de-adivinar-para-produccion")

# Railway asignará el puerto dinámicamente
FLASK_PORT = int(os.getenv("PORT", 5001))

# Orígenes permitidos para CORS
CORS_ALLOWED_ORIGINS = {
    "http://127.0.0.1:52370", 
    "http://localhost:52370",
    "https://chatbot.sialweb.com",
    "http://chatbot.sialweb.com"
}