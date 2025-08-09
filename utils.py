# utils.py — adaptado a multi-negocio y PostgreSQL
import unicodedata
import re
from datetime import datetime, timedelta
import dateparser
from difflib import get_close_matches
import locale
import config

try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')

# ID temporal de negocio (en el futuro vendrá dinámico por slug)
NEGOCIO_ID = 1

def normalizar_texto(texto):
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8', 'ignore').lower()

def validar_nombre(nombre):
    return bool(re.fullmatch(r"[A-Za-zÁÉÍÓÚÑáéíóúñ\s]{2,50}", nombre))

def validar_telefono(telefono):
    return bool(re.fullmatch(r"\d{9}", telefono))

def extraer_hora(texto):
    texto_norm = normalizar_texto(texto)
    match_completo = re.search(r'(\d{1,2})[:h](\d{2})', texto_norm)
    if match_completo:
        hora = int(match_completo.group(1))
        minutos = int(match_completo.group(2))
        return f"{hora:02d}:{minutos:02d}"
        
    palabras_a_numeros = {
        'una': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5, 'seis': 6, 'siete': 7, 
        'ocho': 8, 'nueve': 9, 'diez': 10, 'once': 11, 'doce': 12
    }
    numero_encontrado = None
    for palabra, numero in palabras_a_numeros.items():
        if palabra in texto_norm:
            numero_encontrado = numero
            break
            
    if numero_encontrado is None:
        match_simple = re.search(r'\b(\d{1,2})\b', texto_norm)
        if match_simple:
            numero_encontrado = int(match_simple.group(1))

    if numero_encontrado is not None:
        if 1 <= numero_encontrado <= 8:
            hora = numero_encontrado + 12
        else:
            hora = numero_encontrado
        
        if 'y media' in texto_norm:
            return f"{hora:02d}:30"
        else:
            return f"{hora:02d}:00"

    return None

def detectar_fecha(texto):
    now = datetime.now()
    texto_norm = normalizar_texto(texto)
    
    if "manana" in texto_norm:
        return now + timedelta(days=1)
    if "pasado manana" in texto_norm:
        return now + timedelta(days=2)

    dias_semana = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
    for i, dia_nombre in enumerate(dias_semana):
        if dia_nombre in texto_norm:
            dias_adelante = (i - now.weekday() + 7) % 7
            if dias_adelante == 0: dias_adelante = 7
            return now + timedelta(days=dias_adelante)

    settings = {'PREFER_DATES_FROM': 'future', 'DATE_ORDER': 'DMY'}
    return dateparser.parse(texto, languages=["es"], settings=settings)

def formato_fecha(d):
    return d.strftime("%d/%m/%Y")

def fecha_a_iso(fecha_str):
    """Convierte dd/mm/YYYY a YYYY-MM-DD para PostgreSQL."""
    return datetime.strptime(fecha_str, "%d/%m/%Y").strftime("%Y-%m-%d")

def generar_mensaje_disponibilidad_para_fecha(fecha_obj, negocio_id=NEGOCIO_ID):
    from database import cita_ya_existe
    
    fecha_str = formato_fecha(fecha_obj)
    horas_libres = [h for h in config.HORAS_DISPONIBLES if not cita_ya_existe(fecha_str, h, negocio_id=negocio_id)]

    if not horas_libres:
        return f"Lo siento, no queda ninguna hora libre para el {fecha_str}. ¿Quieres elegir otro día?"

    respuesta = f"👉 Para el día {fecha_str}, estas son las horas disponibles:\n"
    respuesta += ", ".join(horas_libres)
    respuesta += "\n¿Qué hora prefieres?"
    return respuesta

def generar_listado_disponibilidad_completo(negocio_id=NEGOCIO_ID):
    from database import cita_ya_existe
    
    respuesta = "Aquí tienes la disponibilidad para los próximos días:"
    dias_encontrados = 0
    fecha_actual = datetime.now()
    dias_a_revisar = 0

    while dias_encontrados < 6 and dias_a_revisar < 30:
        fecha_actual += timedelta(days=1)
        dias_a_revisar += 1
        
        if fecha_actual.weekday() >= 5: 
            continue
        
        dias_encontrados += 1
        fecha_str = formato_fecha(fecha_actual)
        nombre_dia = fecha_actual.strftime("%A").capitalize()
        
        horas_libres = [h for h in config.HORAS_DISPONIBLES if not cita_ya_existe(fecha_str, h, negocio_id=negocio_id)]
        
        horas_manana = [h for h in horas_libres if int(h.split(':')[0]) < 14]
        horas_tarde = [h for h in horas_libres if int(h.split(':')[0]) >= 14]
        
        respuesta += f"\n\n📅 **{nombre_dia} {fecha_str}**"
        if not horas_libres:
            respuesta += "\n   └ (Completo)"
        else:
            if horas_manana:
                respuesta += f"\n   Mañanas: {', '.join(horas_manana)}"
            if horas_tarde:
                respuesta += f"\n   Tardes:   {', '.join(horas_tarde)}"
            
    return respuesta

def encontrar_servicio_mas_cercano(texto_servicio):
    texto_norm = normalizar_texto(texto_servicio)
    
    if 'mecha' in texto_norm or 'y m' in texto_norm:
        return "Corte Y Mechas"
    
    if 'nino' in texto_norm:
        return "Corte Niño Menor De 12 Años"
        
    if 'y barba' in texto_norm or 'corte bar' in texto_norm:
        return "Corte Y Barba"
        
    if 'de barba' in texto_norm:
        return "Corte De Barba"
        
    if 'caba' in texto_norm or 'corte ca' in texto_norm:
        return "Corte Caballero"
        
    servicios_normalizados = [normalizar_texto(s) for s in config.SERVICIOS]
    coincidencias = get_close_matches(texto_norm, servicios_normalizados, n=1, cutoff=0.6)
    if coincidencias:
        indice = servicios_normalizados.index(coincidencias[0])
        return config.SERVICIOS[indice]

    return None



