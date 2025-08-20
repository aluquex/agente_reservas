# config.py
import os
from urllib.parse import urlparse # Importamos aquí directamente

DATABASE_URL = os.getenv("DATABASE_URL")

# --- Lógica de conexión a prueba de balas ---
if DATABASE_URL:
    result = urlparse(DATABASE_URL)
    DB_USER = result.username
    DB_PASSWORD = result.password
    DB_HOST = result.hostname
    DB_PORT = result.port
    DB_NAME = result.path[1:]
else:
    # Valores para desarrollo local si DATABASE_URL no está
    DB_HOST = "localhost"
    DB_NAME = "chatbot_sialweb_local"
    DB_USER = "postgres"
    DB_PASSWORD = "30980161Nn*"
    DB_PORT = 5432

# El resto de variables
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "30980161Nn*")
SECRET_KEY = os.getenv("SECRET_KEY", "una-clave-secreta-muy-larga-y-dificil-de-adivinar-para-produccion")
FLASK_PORT = int(os.getenv("PORT", 5001))
CORS_ALLOWED_ORIGINS = {
    "http://127.0.0.1:523_0", 
    "http://localhost:52370",
    "https://chatbot.sialweb.com",
    "http://chatbot.sialweb.com"
}