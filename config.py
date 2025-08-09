import os

# Lee la URL de la base de datos desde variable de entorno o usa la de desarrollo por defecto
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:vjUlXFDHMuNbLgrnMLgdGkuEzuRKfJSx@hopper.proxy.rlwy.net:37375/ferrocarril"
)

# Clave secreta para Flask
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")

# Servicios de ejemplo para el negocio actual
SERVICIOS = [
    "Corte Caballero",
    "Corte Y Barba",
    "Corte Niño Menor De 12 Años",
    "Corte De Barba",
    "Corte Y Mechas"
]

# Horarios disponibles para reservas
HORAS_DISPONIBLES = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30",
    "16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00", "19:30"
]
