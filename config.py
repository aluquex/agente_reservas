# config.py
import os
import dj_database_url

# --- LECTURA DE VARIABLES A PRUEBA DE APOCALIPSIS ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("No se ha encontrado la variable de entorno DATABASE_URL. El servicio no puede arrancar.")

db_config = dj_database_url.config(default=DATABASE_URL)
DB_USER = db_config.get('USER')
DB_PASSWORD = db_config.get('PASSWORD')
DB_HOST = db_config.get('HOST')
DB_PORT = db_config.get('PORT')
DB_NAME = db_config.get('NAME')

# El resto de variables las definimos directamente o las leemos de forma segura
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "30980161Nn*")
SECRET_KEY = os.getenv("SECRET_KEY", "una-clave-secreta-muy-larga-y-dificil-de-adivinar-para-produccion")
FLASK_PORT = int(os.getenv("PORT", 5001))
CORS_ALLOWED_ORIGINS = {
    "http://127.0.0.1:52370", 
    "http://localhost:52370",
    "https://chatbot.sialweb.com",
    "http://chatbot.sialweb.com"
}