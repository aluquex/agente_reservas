# config.py
import os
import dj_database_url
from dotenv import load_dotenv

# Carga las variables del archivo .env si existe (para desarrollo local)
load_dotenv()

# Prioridad 1: Usar la URL de la base de datos que Railway inyecta
database_url = os.getenv("DATABASE_URL")

if database_url:
    # dj_database_url parsea la URL y devuelve un diccionario con todas las claves
    db_config = dj_database_url.config(default=database_url)
    DB_USER = db_config.get('USER')
    DB_PASSWORD = db_config.get('PASSWORD')
    DB_HOST = db_config.get('HOST')
    DB_PORT = db_config.get('PORT')
    DB_NAME = db_config.get('NAME')
else:
    # Prioridad 2: Si no hay DATABASE_URL, usamos los valores locales
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