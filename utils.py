# utils.py
import unicodedata
from datetime import datetime
from difflib import get_close_matches
# Ya no necesitamos el módulo locale, lo quitamos para evitar confusiones.

def normalizar_texto(texto):
    texto = texto.lower()
    nfkd_form = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def validar_nombre(nombre):
    return len(nombre) > 2 and all(c.isalpha() or c.isspace() for c in nombre)

def encontrar_servicio_mas_cercano(texto, lista_servicios):
    texto_norm = normalizar_texto(texto)
    servicios_norm = {normalizar_texto(s): s for s in lista_servicios}
    
    mejores_coincidencias = get_close_matches(texto_norm, servicios_norm.keys(), n=1, cutoff=0.6)
    
    if mejores_coincidencias:
        return servicios_norm[mejores_coincidencias[0]]
    return None

def now_spain():
    return datetime.now()

# --- LA SOLUCIÓN A PRUEBA DE BALAS ---
def formato_nombre_dia_es(fecha_obj):
    """
    Devuelve el nombre del día de la semana en español, con tildes,
    sin depender de la configuración 'locale' del sistema.
    """
    dias_es = {
        0: "Lunes",
        1: "Martes",
        2: "Miércoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sábado",
        6: "Domingo"
    }
    # .weekday() devuelve un número de 0 (lunes) a 6 (domingo)
    return dias_es.get(fecha_obj.weekday(), "")

def ha_pasado_fecha_hora(fecha, hora):
    ahora = datetime.now()
    fecha_hora_cita = datetime.combine(fecha, hora)
    return ahora > fecha_hora_cita