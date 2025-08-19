# config.py
ADMIN_PASSWORD = "30980161Nn*"
DB_HOST = "localhost"
DB_NAME = "chatbot_sialweb_local"
DB_USER = "postgres"
DB_PASSWORD = "30980161Nn*"
# --- CORRECCIÓN FINAL: Añadimos la variable DB_PORT ---
DB_PORT = 5432 # El puerto estándar para PostgreSQL
SECRET_KEY = "la-clave-definitiva-para-que-funcione"
FLASK_PORT = 5001
CORS_ALLOWED_ORIGINS = { "http://127.0.0.1:52370", "http://localhost:52370" }