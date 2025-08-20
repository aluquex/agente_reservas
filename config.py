# config.py
import os

# --- CREDENCIALES PARA PRODUCCIÓN (RAILWAY) ---
# Leemos las variables de entorno si existen, si no, usamos estos valores.
# En Railway configuraremos las variables de entorno para máxima seguridad.

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "30980161Nn*")

# Extraído de tu URL de conexión de Railway:
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "vjUlXFDHMuNbLgrnMLgdGkuEzuRKfJSx")
DB_HOST = os.getenv("DB_HOST", "hopper.proxy.rlwy.net")
DB_PORT = int(os.getenv("DB_PORT", 37375))
DB_NAME = os.getenv("DB_NAME", "railway")

# La SECRET_KEY es vital para la seguridad de las sesiones en producción
SECRET_KEY = os.getenv("SECRET_KEY", "una-clave-secreta-muy-larga-y-dificil-de-adivinar-para-produccion")

# Railway asignará el puerto dinámicamente, por eso leemos la variable de entorno 'PORT'
FLASK_PORT = int(os.getenv("PORT", 5001))

# Orígenes permitidos para CORS. Cuando subamos a Hostinger, añadiremos tu dominio.
CORS_ALLOWED_ORIGINS = {
    "http://127.0.0.1:52370", 
    "http://localhost:52370",
    "https://chatbot.sialweb.com", # ¡Añadimos tu subdominio de producción!
    "http://chatbot.sialweb.com"
}