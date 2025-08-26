# config.py
import os
import dj_database_url
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    db_config = dj_database_url.config(default=DATABASE_URL)
    DB_USER = db_config.get('USER')
    DB_PASSWORD = db_config.get('PASSWORD')
    DB_HOST = db_config.get('HOST')
    DB_PORT = db_config.get('PORT')
    DB_NAME = db_config.get('NAME')
else:
    DB_HOST = "localhost"
    DB_NAME = "chatbot_sialweb_local"
    DB_USER = "postgres"
    DB_PASSWORD = "30980161Nn*"
    DB_PORT = 5432

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "30980161Nn*")
SECRET_KEY = os.getenv("SECRET_KEY", "una-clave-secreta-muy-larga-y-dificil-de-adivinar-para-produccion")
FLASK_PORT = int(os.getenv("PORT", 5001))
CORS_ALLOWED_ORIGINS = {
    "http://127.0.0.1:52370", 
    "http://localhost:52370",
    "https://chatbot.sialweb.com",
    "http://chatbot.sialweb.com"
}

# --- NUEVAS VARIABLES PARA NOTIFICACIONES POR EMAIL ---
# El email desde el que se enviarán las notificaciones
MAIL_SENDER = os.getenv("MAIL_SENDER", "aluquex@gmail.com") 
# La contraseña de aplicación de 16 letras que has generado
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "rgtl fono vljj pple") 