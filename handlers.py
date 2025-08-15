# handlers.py
from flask import session
from datetime import timedelta, datetime
import utils
import database

HORAS_JORNADA = ["10:00", "11:00", "12:00", "13:00", "16:00", "17:00", "18:00", "19:00"]

def _get_negocio_id():
    return session.get('negocio_id', 1)

# --- FLUJO DE NUEVA RESERVA ---
def handle_bienvenida(_texto_usuario):
    session.clear(); session['negocio_id'] = 1; session['estado'] = 'pidiendo_nombre'
    return {"respuesta": "¡Buenas! Bienvenido a Peluquería Sialweb. Para empezar, ¿cómo te llamas?"}

def handle_peticion_nombre(texto_usuario):
    session['nombre'] = texto_usuario.strip().title(); session['estado'] = 'pidiendo_telefono'
    return {"respuesta": f"¡Genial, {session['nombre']}! Ahora dime tu número de móvil."}

def handle_peticion_telefono(texto_usuario):
    telefono = texto_usuario.strip(); session['telefono'] = telefono
    if database.tiene_cita_futura(telefono, negocio_id=_get_negocio_id()):
        session.clear(); return { "respuesta": "¡Ojo! Ya tienes una cita pendiente. Si quieres gestionarla, dímelo." }
    mensaje_inicial = "¡Recibido! Estos son nuestros servicios:"
    pregunta_final = "\n\n¿Qué te vas a hacer hoy?"
    citas_pasadas = database.obtener_citas_pasadas(telefono, negocio_id=_get_negocio_id())
    if citas_pasadas:
        ultima_cita = citas_pasadas[0]; fecha_legible = ultima_cita['fecha'].strftime('%d de %B')
        saludo_recurrente = (f"¡Qué bueno verte de nuevo, {session['nombre']}! Tu última visita fue el {fecha_legible} para un '{ultima_cita['servicio_nombre']}'.")
        mensaje_inicial = f"{saludo_recurrente}\n\n¿Qué te vas a hacer hoy? Nuestros servicios son:"
        pregunta_final = ""
    session['estado'] = 'pidiendo_servicio'
    servicios_db = database.listar_servicios(negocio_id=_get_negocio_id())
    nombres_servicios = [s['nombre'] for s in servicios_db]
    session['nombres_servicios_disponibles'] = nombres_servicios
    lista_servicios_str = ""
    for servicio in servicios_db: lista_servicios_str += f"\n› {servicio['nombre']} — {servicio['precio']}€"
    respuesta_completa = f"{mensaje_inicial}{lista_servicios_str}{pregunta_final}"
    return {"respuesta": respuesta_completa}

def handle_peticion_servicio(texto_usuario):
    if session.get('modificando_cita'): return handle_modificar_servicio(texto_usuario)
    nombres_servicios = session.get('nombres_servicios_disponibles', [])
    servicio_elegido = utils.encontrar_servicio_mas_cercano(texto_usuario, nombres_servicios)
    if not servicio_elegido: return {"respuesta": "No he entendido. Elige uno de los servicios."}
    session['servicio'] = servicio_elegido; session['estado'] = 'pidiendo_hora'
    return _mostrar_calendario()

def handle_peticion_hora(texto_usuario):
    if session.get('modificando_cita'): return handle_modificar_fecha_hora(texto_usuario)
    return _mostrar_horas_para_fecha(texto_usuario)

def handle_confirmar_cita(texto_usuario):
    session['hora'] = texto_usuario.strip()
    try:
        datos_para_guardar = { "nombre": session.get('nombre'), "telefono": session.get('telefono'), "servicio": session.get('servicio'), "fecha": session.get('fecha'), "hora": session.get('hora') }
        database.guardar_reserva(datos_para_guardar, negocio_id=_get_negocio_id())
    except Exception as e:
        print(f"!!! ERROR al guardar: {e}"); return {"respuesta": "¡Uy! Ha ocurrido un error al confirmar tu cita."}
    nombre_usuario = session.get('nombre', 'Cliente'); fecha_legible = datetime.strptime(session.get('fecha'), '%Y-%m-%d').strftime('%d/%m/%Y')
    respuesta_final = ( f"¡Tachán! Cita confirmada, {nombre_usuario}.\n\n" f"**Resumen:**\n" f"› Servicio: {session.get('servicio')}\n" f"› Día: {fecha_legible}\n" f"› Hora: {session.get('hora')}\n\n" "¡Gracias! Te esperamos." )
    session.clear(); return {"respuesta": respuesta_final}

# --- FLUJO DE GESTIÓN ---
def handle_inicio_gestion(texto_usuario):
    session.clear(); session['negocio_id'] = 1
    texto_norm = utils.normalizar_texto(texto_usuario)
    if 'cancelar' in texto_norm or 'anular' in texto_norm: session['accion_gestion'] = 'cancelar'
    elif 'modificar' in texto_norm or 'cambiar' in texto_norm: session['accion_gestion'] = 'modificar'
    else: session['accion_gestion'] = 'consultar'
    session['estado'] = 'gestion_pide_telefono'
    return {"respuesta": "¡Claro! Para encontrar tu cita, dime tu número de teléfono."}

def handle_gestion_pide_telefono(texto_usuario):
    telefono = texto_usuario.strip()
    citas_futuras = database.obtener_citas_futuras_por_telefono(telefono, negocio_id=_get_negocio_id())
    if not citas_futuras:
        session.clear(); return {"respuesta": "No he encontrado ninguna cita pendiente con ese teléfono."}
    cita = citas_futuras[0]
    cita_serializable = { "id": cita['id'], "fecha": cita['fecha'].strftime('%Y-%m-%d'), "hora": cita['hora'].strftime('%H:%M'), "servicio_nombre": cita['servicio_nombre'] }
    session['cita_a_gestionar'] = cita_serializable
    fecha_legible = cita['fecha'].strftime('%A, %d de %B'); hora_legible = cita['hora'].strftime('%H:%M')
    mensaje_intro = f"He encontrado tu cita para un **'{cita['servicio_nombre']}'** el **{fecha_legible} a las {hora_legible}**."
    if session.get('accion_gestion') == 'consultar':
        session.clear(); return { "respuesta": mensaje_intro }
    if session.get('accion_gestion') == 'cancelar':
        session['estado'] = 'gestion_confirmar_cancelacion'
        return { "respuesta": f"{mensaje_intro}\n\n¿Estás seguro de que quieres cancelarla? (sí/no)" }
    if session.get('accion_gestion') == 'modificar':
        session['estado'] = 'gestion_pide_campo_a_modificar'
        return { "respuesta": f"{mensaje_intro}\n\n¿Qué te gustaría cambiar: el **servicio** o el **día/hora**?" }

def handle_gestion_confirmar_cancelacion(texto_usuario):
    respuesta_norm = utils.normalizar_texto(texto_usuario)
    if respuesta_norm in ['si', 's', 'sip', 'confirmo', 'cancelala']:
        cita_a_cancelar = session.get('cita_a_gestionar')
        if cita_a_cancelar:
            database.cancelar_cita(cita_a_cancelar['id'], negocio_id=_get_negocio_id()); session.clear()
            return {"respuesta": "¡Hecho! Tu cita ha sido cancelada."}
    elif respuesta_norm in ['no', 'n', 'nop', 'no cancelar']:
        session.clear(); return {"respuesta": "De acuerdo. No he cancelado tu cita."}
    else: return {"respuesta": "No te he entendido. Responde 'sí' para confirmar o 'no'."}

def handle_gestion_pide_campo_a_modificar(texto_usuario):
    texto_norm = utils.normalizar_texto(texto_usuario)
    session['modificando_cita'] = True
    if 'servicio' in texto_norm:
        session['estado'] = 'pidiendo_servicio'
        servicios_db = database.listar_servicios(negocio_id=_get_negocio_id())
        nombres_servicios = [s['nombre'] for s in servicios_db]
        session['nombres_servicios_disponibles'] = nombres_servicios
        lista_servicios_str = ""
        for s in servicios_db: lista_servicios_str += f"\n› {s['nombre']} — {s['precio']}€"
        return {"respuesta": f"Entendido. ¿Por cuál de estos servicios quieres cambiarla?{lista_servicios_str}"}
    elif 'dia' in texto_norm or 'hora' in texto_norm or 'fecha' in texto_norm:
        session['estado'] = 'pidiendo_hora'
        return _mostrar_calendario()
    else: return {"respuesta": "No te he entendido. Dime si quieres cambiar el **servicio** o el **día/hora**."}

# --- FUNCIONES AUXILIARES Y DE MODIFICACIÓN ---
def _mostrar_calendario():
    dias_disponibles = []; hoy = utils.now_spain().date(); dia_actual = hoy
    while dia_actual.month == hoy.month:
        if dia_actual.weekday() >= 5: dia_actual += timedelta(days=1); continue
        dias_disponibles.append({ "display": f"{utils.formato_nombre_dia_es(dia_actual)} {dia_actual.strftime('%d/%m')}", "value": dia_actual.strftime('%Y-%m-%d') })
        dia_actual += timedelta(days=1)
    return { "respuesta": "De acuerdo, elige un nuevo día del calendario:", "ui_component": { "type": "day_selector", "days": dias_disponibles } }

def _mostrar_horas_para_fecha(fecha_str):
    try:
        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        session['fecha'] = fecha_str
        horas_ocupadas = database.obtener_horas_ocupadas(fecha_str, negocio_id=_get_negocio_id())
        ahora = utils.now_spain(); horas_libres = []
        for hora_str in HORAS_JORNADA:
            if hora_str in horas_ocupadas: continue
            hora_cita = int(hora_str.split(":")[0])
            if fecha_obj == ahora.date() and hora_cita <= ahora.hour: continue
            horas_libres.append(hora_str)
        if session.get('modificando_cita'): session['estado'] = 'modificar_confirmar_hora'
        else: session['estado'] = 'confirmar_cita'
        if not horas_libres: return {"respuesta": f"Vaya, para el día {fecha_obj.strftime('%d/%m')} no quedan huecos."}
        return { "respuesta": f"Estupendo. Para el día {fecha_obj.strftime('%d/%m')} tengo hueco en estas horas:", "ui_component": { "type": "hour_selector", "hours": horas_libres } }
    except ValueError:
        return {"respuesta": "No he entendido la fecha que has seleccionado."}

def handle_modificar_servicio(texto_usuario):
    nombres_servicios = session.get('nombres_servicios_disponibles', [])
    nuevo_servicio = utils.encontrar_servicio_mas_cercano(texto_usuario, nombres_servicios)
    if not nuevo_servicio: return {"respuesta": "No he reconocido ese servicio. Elige uno de la lista."}
    cita_id = session['cita_a_gestionar']['id']
    database.modificar_cita(cita_id, _get_negocio_id(), {'servicio': nuevo_servicio})
    session.clear()
    return {"respuesta": f"¡Listo! He cambiado el servicio de tu cita a **'{nuevo_servicio}'**. El día y la hora se mantienen."}

def handle_modificar_fecha_hora(texto_usuario):
    return _mostrar_horas_para_fecha(texto_usuario)

def handle_modificar_confirmar_hora(texto_usuario):
    hora_elegida = texto_usuario.strip()
    cita_id = session['cita_a_gestionar']['id']
    nuevos_datos = { 'fecha': session.get('fecha'), 'hora': hora_elegida }
    database.modificar_cita(cita_id, _get_negocio_id(), nuevos_datos)
    session.clear()
    fecha_legible = datetime.strptime(nuevos_datos['fecha'], '%Y-%m-%d').strftime('%d/%m/%Y')
    return {"respuesta": f"¡Cita actualizada! Tu nueva cita es el **{fecha_legible} a las {hora_elegida}**."}