# handlers.py — versión multi-negocio
from flask import jsonify, session
import utils
import config
import database

# Config temporal: negocio fijo
NEGOCIO_ID = 1

# --- MANEJADORES DE CITA NUEVA ---

def handle_bienvenida(texto_usuario):
    session.clear()
    session['estado'] = 'pidiendo_nombre'
    return jsonify({"respuesta": "¡Hola! Bienvenido a la peluquería Alejandro Luque. ¿cómo te llamas?"})

def handle_peticion_nombre(texto_usuario):
    if not utils.validar_nombre(texto_usuario):
        return jsonify({"respuesta": "Por favor, introduce un nombre válido."})
    session['nombre'] = texto_usuario.title()
    session['estado'] = 'pidiendo_telefono'
    servicios_str = "\n".join([f"💈 {s}" for s in config.SERVICIOS])
    return jsonify({"respuesta": f"Encantado, {session['nombre']}. ¿Cuál es tu número de teléfono?"})

def handle_peticion_telefono(texto_usuario):
    telefono = texto_usuario.replace(" ", "")
    if not utils.validar_telefono(telefono):
        return jsonify({"respuesta": "Introduce un teléfono válido de 9 dígitos."})
    session['telefono'] = telefono
    session['estado'] = 'pidiendo_servicio'
    servicios_str = "\n".join([f"💈 {s}" for s in config.SERVICIOS])
    return jsonify({"respuesta": f"Perfecto. Nuestros servicios:\n{servicios_str}\n¿Cuál deseas?"})

def handle_peticion_servicio(texto_usuario):
    servicio_elegido = utils.encontrar_servicio_mas_cercano(texto_usuario)
    if not servicio_elegido:
        return jsonify({"respuesta": "No he reconocido ese servicio. Elige uno de la lista."})
    
    session['servicio'] = servicio_elegido
    
    if session.get('modificando_cita_id'):
        return confirmar_modificacion()

    session['estado'] = 'pidiendo_fecha'
    mensaje = (f"Has elegido '{servicio_elegido}'.\n"
               f"{utils.generar_listado_disponibilidad_completo()}\n\n"
               "Dime qué día te viene bien (p. ej., 'el jueves').")
    return jsonify({"respuesta": mensaje})

def handle_peticion_fecha(texto_usuario):
    fecha_obj = utils.detectar_fecha(texto_usuario)
    if not fecha_obj:
        return jsonify({"respuesta": "No he entendido la fecha. Inténtalo de nuevo."})
    if fecha_obj.weekday() >= 5 or fecha_obj.date() < utils.datetime.now().date():
        return jsonify({"respuesta": "Fecha no válida. Elige un día laborable futuro."})
        
    session['fecha'] = utils.formato_fecha(fecha_obj)
    
    if session.get('modificando_cita_id'):
        return confirmar_modificacion()

    session['estado'] = 'pidiendo_hora'
    return jsonify({"respuesta": utils.generar_mensaje_disponibilidad_para_fecha(fecha_obj)})

def handle_peticion_hora(texto_usuario):
    hora_elegida = utils.extraer_hora(texto_usuario)
    if not hora_elegida or hora_elegida not in config.HORAS_DISPONIBLES:
        return jsonify({"respuesta": "Hora no válida. Elige una de las propuestas."})

    if database.cita_ya_existe(session['fecha'], hora_elegida, negocio_id=NEGOCIO_ID):
        return jsonify({"respuesta": f"La hora {hora_elegida} ya está ocupada. Elige otra."})

    session['hora'] = hora_elegida
    
    if session.get('modificando_cita_id'):
        return confirmar_modificacion()

    nueva_reserva = {
        "nombre": session['nombre'],
        "telefono": session['telefono'],
        "servicio": session['servicio'],
        "fecha": session['fecha'],
        "hora": session['hora']
    }
    database.anadir_reserva(nueva_reserva, negocio_id=NEGOCIO_ID)
    respuesta = (f"✅ ¡Todo listo, {session['nombre']}! Tu cita está confirmada:\n\n"
                 f"📅 Fecha: {session['fecha']}\n"
                 f"⏰ Hora: {session['hora']}\n"
                 f"💈 Servicio: {session['servicio']}\n\n¡Nos vemos!")
    session.clear()
    return jsonify({"respuesta": respuesta})

# --- MANEJADORES DE GESTIÓN (CONSULTA, CANCELACIÓN, MODIFICACIÓN) ---

def handle_inicio_gestion(texto_usuario):
    session.clear()
    texto_norm = utils.normalizar_texto(texto_usuario)
    
    if "consultar" in texto_norm: session['accion'] = 'consultar'
    elif "cancelar" in texto_norm: session['accion'] = 'cancelar'
    elif "modificar" in texto_norm: session['accion'] = 'modificar'
    
    session['estado'] = 'gestion_pide_telefono'
    return jsonify({"respuesta": "Entendido. Para continuar, introduce tu número de teléfono."})

def handle_gestion_pide_telefono(texto_usuario):
    telefono = texto_usuario.replace(" ", "")
    if not utils.validar_telefono(telefono):
        return jsonify({"respuesta": "Número no válido. Introduce un teléfono de 9 dígitos."})
    
    citas = database.get_citas_por_telefono(telefono, negocio_id=NEGOCIO_ID)
    if not citas:
        session.clear()
        return jsonify({"respuesta": "No he encontrado ninguna cita con ese número."})

    cita = citas[0]
    
    if session['accion'] == 'consultar':
        respuesta = f"He encontrado tu cita:\n\n📅 Fecha: {cita['fecha']}\n⏰ Hora: {cita['hora']}\n💈 Servicio: {cita['servicio']}"
        session.clear()
        return jsonify({"respuesta": respuesta})
        
    elif session['accion'] == 'cancelar':
        session['cita_gestionada_id'] = cita['id']
        session['estado'] = 'gestion_confirmar_cancelacion'
        return jsonify({"respuesta": f"He encontrado esta cita:\n\n📅 {cita['fecha']} a las {cita['hora']}\n\n¿Seguro que quieres cancelarla? (sí/no)"})
        
    elif session['accion'] =="modificar":
        session['modificando_cita_id'] = cita['id']
        session['servicio'] = cita['servicio']
        session['fecha'] = cita['fecha']
        session['hora'] = cita['hora']
        session['estado'] = 'modificar_pide_campo'
        return jsonify({"respuesta": f"Ok. Tu cita actual es:\n📅 {cita['fecha']} a las {cita['hora']} para un '{cita['servicio']}'.\n\n¿Qué quieres modificar: el servicio, la fecha o la hora?"})

def handle_gestion_confirmar_cancelacion(texto_usuario):
    texto_norm = utils.normalizar_texto(texto_usuario)
    if texto_norm in ['si', 'sip', 'confirmo', 'cancelar']:
        database.cancelar_cita(session['cita_gestionada_id'], negocio_id=NEGOCIO_ID)
        session.clear()
        return jsonify({"respuesta": "Gracias, la cita ha sido cancelada con éxito. Hasta la próxima"})
    elif texto_norm in ['no', 'nop', 'no cancelar']:
        session.clear()
        return jsonify({"respuesta": "De acuerdo, no he cancelado tu cita."})
    else:
        return jsonify({"respuesta": "Responde 'sí' para cancelar o 'no' para mantener la cita."})

# --- NUEVOS MANEJADORES PARA MODIFICACIÓN ---

def handle_modificar_pide_campo(texto_usuario):
    texto_norm = utils.normalizar_texto(texto_usuario)
    if 'servicio' in texto_norm:
        session['estado'] = 'pidiendo_servicio'
        servicios_str = "\n".join([f"💈 {s}" for s in config.SERVICIOS])
        return jsonify({"respuesta": f"Ok, elige el nuevo servicio:\n{servicios_str}"})
    elif 'fecha' in texto_norm:
        session['estado'] = 'pidiendo_fecha'
        mensaje = (f"{utils.generar_listado_disponibilidad_completo()}\n\n"
                   "Elige una nueva fecha.")
        return jsonify({"respuesta": mensaje})
    elif 'hora' in texto_norm:
        session['estado'] = 'pidiendo_hora'
        fecha_obj = utils.datetime.strptime(session['fecha'], '%d/%m/%Y')
        return jsonify({"respuesta": utils.generar_mensaje_disponibilidad_para_fecha(fecha_obj)})
    else:
        return jsonify({"respuesta": "Por favor, dime si quieres cambiar 'servicio', 'fecha' u 'hora'."})

def confirmar_modificacion():
    datos_nuevos = {
        'servicio': session['servicio'],
        'fecha': session['fecha'],
        'hora': session['hora']
    }
    id_cita = session['modificando_cita_id']
    
    database.actualizar_cita(id_cita, datos_nuevos, negocio_id=NEGOCIO_ID)
    
    cita_actualizada = database.get_cita_por_id(id_cita, negocio_id=NEGOCIO_ID)
    
    respuesta = (f"GRACIAS, SU CITA HA SIDO MODIFICADA.\n\n"
                 f"Aquí tienes los nuevos datos:\n"
                 f"📅 Fecha: {cita_actualizada['fecha']}\n"
                 f"⏰ Hora: {cita_actualizada['hora']}\n"
                 f"💈 Servicio: {cita_actualizada['servicio']}")
                 
    session.clear()
    return jsonify({"respuesta": respuesta})

def handle_fallback(texto_usuario):
    return jsonify({"respuesta": "Lo siento, no he entendido. Puedes pedir 'nueva cita', 'consultar', 'modificar' o 'cancelar'."})
