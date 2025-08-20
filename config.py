# config.py
import os
from urllib.parse import urlparse

# Prioridad 1: Usar la URL de la base de datos que Railway inyecta
database_url = os.getenv("DATABASE_URL")

if database_url:
    # Si estamos en producción (Railway), parseamos la URL para obtener las credenciales
    result = urlparse(database_url)
    DB_USER = result.username
    DB_PASSWORD = result.password
    DB_HOST = result.hostname
    DB_PORT = result.port
    DB_NAME = result.path[1:]
else:
    # Prioridad 2: Si no hay DATABASE_URL, leemos las variables individuales
    # Esto es útil si en el futuro usamos otro proveedor que no inyecte la URL completa
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_NAME = os.getenv("DB_NAME", "chatbot_sialweb_local")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "30980161Nn*")
    DB_PORT = int(os.getenv("DB_PORT", 5432))

# El resto de variables no cambian
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "30980161Nn*")
SECRET_KEY = os.getenv("SECRET_KEY", "una-clave-secreta-muy-larga-y-dificil-de-adivinar-para-produccion")
FLASK_PORT = int(os.getenv("PORT", 5001))
CORS_ALLOWED_ORIGINS = {
    "http://127.0.0.1:52370", 
    "http://localhost:52370",
    "https://chatbot.sialweb.com",
    "http://chatbot.sialweb.com"
}