# utils.py
import unicodedata
from difflib import get_close_matches
from datetime import datetime
import pytz
import locale
import re

try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')

def normalizar_texto(texto):
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8', 'ignore').lower()

def validar_nombre(nombre):
    if not nombre or len(nombre) < 2 or len(nombre) > 50: return False
    return bool(re.fullmatch(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', nombre))

def encontrar_servicio_mas_cercano(texto_usuario, lista_servicios):
    texto_normalizado = normalizar_texto(texto_usuario)
    coincidencias = get_close_matches(texto_normalizado, lista_servicios, n=1, cutoff=0.6)
    if coincidencias: return coincidencias[0]
    else: return None

def now_spain():
    tz_spain = pytz.timezone('Europe/Madrid')
    return datetime.now(tz_spain)

def formato_nombre_dia_es(fecha_obj):
    return fecha_obj.strftime('%A').capitalize()

# --- NUEVA HERRAMIENTA DE PRECISIÓN ---
def ha_pasado_fecha_hora(fecha, hora):
    """
    Comprueba si una fecha y hora dadas ya han ocurrido.
    'fecha' es un objeto date.
    'hora' es un objeto time.
    """
    ahora = now_spain()
    # Creamos un objeto datetime consciente de la zona horaria para la cita
    cita_dt = pytz.timezone('Europe/Madrid').localize(datetime.combine(fecha, hora))
    return cita_dt < ahora