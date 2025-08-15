# utils.py
# =========================================
# Nuestra "caja de herramientas".
# Ahora con capacidad para mostrar días en español.
# =========================================
import unicodedata
from difflib import get_close_matches
from datetime import datetime
import pytz
import locale

# --- Configuración del idioma español ---
try:
    # Para sistemas Linux/macOS
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    # Para sistemas Windows
    locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')

def normalizar_texto(texto):
    """
    Limpia y estandariza el texto: quita acentos, convierte a minúsculas, etc.
    """
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8', 'ignore').lower()

def encontrar_servicio_mas_cercano(texto_usuario, lista_servicios):
    """
    Compara el texto del usuario con una lista de servicios válidos
    y encuentra la coincidencia más probable.
    """
    texto_normalizado = normalizar_texto(texto_usuario)
    coincidencias = get_close_matches(texto_normalizado, lista_servicios, n=1, cutoff=0.6)
    if coincidencias:
        return coincidencias[0]
    else:
        return None

def now_spain():
    """
    Devuelve la fecha y hora actual en la zona horaria de España.
    """
    tz_spain = pytz.timezone('Europe/Madrid')
    return datetime.now(tz_spain)

def formato_nombre_dia_es(fecha_obj):
    """
    Devuelve el nombre del día de la semana en español y capitalizado.
    Ej: 'Lunes', 'Martes', etc.
    """
    # LÍNEA CORREGIDA: Se han eliminado las comillas extra al final
    return fecha_obj.strftime('%A').capitalize()