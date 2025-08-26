# handlers.py
from flask import session
from datetime import timedelta, datetime
import utils
import database
import email_manager

def _get_negocio_id():
    return session.get('negocio_id')

def _get_negocio_nombre():
    return session.get('negocio_nombre', 'nuestro negocio')

def _limpiar_sesion_conversacion():
    """Elimina solo los datos de la conversación actual, preservando el negocio."""
    claves_a_borrar = [
        'estado', 'nombre', 'telefono', 'servicio', 'empleado_id',
        'empleado_nombre', 'empleados_disponibles', 'fecha', 'hora',
        'nombres_servicios_disponibles', 'cita_a_gestionar', 'modificando_cita',
        'email_cliente', 'es_recurrente'
    ]
    for clave in claves_a_borrar:
        session.pop(clave, None)

def handle_bienvenida(_texto_usuario):
    _limpiar_sesion_conversacion()
    return {
        "respuesta": f"BIENVENIDO/A A { _get_negocio_nombre().upper() }, ¿quieres agendar una cita o gestionar una ya existente?",
        "ui_component": { "type": "choice_buttons", "choices": ["Agendar Cita", "Gestionar Cita"] },
        "nuevo_estado": "esperando_eleccion_inicial"
    }

def handle_eleccion_inicial(texto_usuario):
    texto_norm = utils.normalizar_texto(texto_usuario)
    if "agendar" in texto_norm:
        return {"respuesta": "¡Perfecto! Vamos a agendar una nueva cita. Para empezar, ¿cómo te llamas?", "nuevo_estado": "pidiendo_nombre"}
    elif "gestionar" in texto_norm:
        return {"respuesta": "¡Claro! Para encontrar tu cita, dime tu número de teléfono.", "nuevo_estado": "gestion_pide_telefono"}
    else:
        return {
            "respuesta": "No te he entendido. Elige una de las opciones:",
            "ui_component": { "type": "choice_buttons", "choices": ["Agendar Cita", "Gestionar Cita"] },
            "nuevo_estado": "esperando_eleccion_inicial"
        }

def handle_peticion_nombre(texto_usuario):
    nombre_usuario = texto_usuario.strip()
    if not utils.validar_nombre(nombre_usuario):
        return {"respuesta": "Lo siento, eso no parece un nombre válido.", "nuevo_estado": "pidiendo_nombre"}
    session['nombre'] = nombre_usuario.title()
    return {"respuesta": f"¡Genial, {session['nombre']}! Ahora dime tu número de móvil.", "nuevo_estado": "pidiendo_telefono"}

def _saludo_recurrente_desde_cita(cita):
    # cita: dict devuelto por database.obtener_ultima_cita_pasada(...)
    try:
        fecha_legible = cita['fecha'].strftime('%d de %B')
        servicio = cita.get('servicio_nombre') or 'servicio'
        nombre = session.get('nombre') or cita.get('nombre_cliente') or 'Cliente'
        return f"¡Qué bueno verte de nuevo, {nombre}! Tu última visita fue el {fecha_legible} para un '{servicio}'."
    except Exception:
        return "¡Qué bueno verte de nuevo!"

def _mostrar_servicios_con_saludo(mensaje_inicial="¡Perfecto!"):
    servicios_db = database.listar_servicios(negocio_id=_get_negocio_id())
    nombres_servicios = [s['nombre'] for s in servicios_db]
    session['nombres_servicios_disponibles'] = nombres_servicios
    botones_servicios = [f"{s['nombre']} — {s['precio']}€" for s in servicios_db]
    respuesta_completa = f"{mensaje_inicial}\n\n¿Qué te vas a hacer hoy? Estos son nuestros servicios:"
    return {
        "respuesta": respuesta_completa,
        "ui_component": { "type": "choice_buttons", "choices": botones_servicios },
        "nuevo_estado": "pidiendo_servicio"
    }

def handle_peticion_telefono(texto_usuario):
    telefono = texto_usuario.strip()
    session['telefono'] = telefono

    # Si ya tiene una cita futura, avisamos y reiniciamos el flujo para que gestione
    if database.tiene_cita_futura(telefono, negocio_id=_get_negocio_id()):
        session.clear()
        respuesta_reinicio = handle_bienvenida("")
        return {
            "respuesta": "¡Ojo! Ya tienes una cita pendiente. Si quieres gestionarla, empieza de nuevo y elige 'Gestionar Cita'.",
            "post_respuesta": respuesta_reinicio,
            "nuevo_estado": "esperando_eleccion_inicial"
        }

    # --- Reconocimiento de usuario recurrente (cita pasada) ---
    ultima_pasada = database.obtener_ultima_cita_pasada(telefono, negocio_id=_get_negocio_id())
    if ultima_pasada:
        session['es_recurrente'] = True
        # Intentar recuperar email previo si existe en la tabla clientes
        email_prev = None
        try:
            email_prev = database.obtener_email_cliente(telefono, _get_negocio_id())
        except Exception:
            email_prev = None

        if email_prev:
            session['email_cliente'] = email_prev
            saludo = _saludo_recurrente_desde_cita(ultima_pasada)
            # Salta pedir email, vamos directo a servicios
            return _mostrar_servicios_con_saludo(mensaje_inicial=saludo)
        else:
            # No tenemos email persistido: mantenemos pedir email para notificaciones al usuario
            saludo = _saludo_recurrente_desde_cita(ultima_pasada)
            return {
                "respuesta": f"{saludo}\n\nPara enviarte la confirmación, ¿qué email prefieres usar?",
                "nuevo_estado": "pidiendo_email"
            }

    # Usuario nuevo (sin citas pasadas): pedir email como antes
    return {"respuesta": "¡Gracias! Y por último, ¿a qué dirección de correo electrónico te enviamos la confirmación de la cita?", "nuevo_estado": "pidiendo_email"}

def handle_peticion_email(texto_usuario):
    email = texto_usuario.strip()
    if not utils.validar_email(email):
        return {"respuesta": "Lo siento, esa dirección de correo no parece válida. Por favor, introdúcela de nuevo.", "nuevo_estado": "pidiendo_email"}

    session['email_cliente'] = email

    mensaje_inicial = "¡Perfecto!"
    # Si es recurrente, personalizamos el saludo
    try:
        citas_pasadas = database.obtener_citas_pasadas(session['telefono'], negocio_id=_get_negocio_id())
        if citas_pasadas:
            ultima_cita = citas_pasadas[0]
            fecha_legible = ultima_cita['fecha'].strftime('%d de %B')
            saludo_recurrente = f"¡Qué bueno verte de nuevo, {session.get('nombre','')}! Tu última visita fue el {fecha_legible} para un '{ultima_cita['servicio_nombre']}'."
            mensaje_inicial = saludo_recurrente
    except Exception:
        pass

    return _mostrar_servicios_con_saludo(mensaje_inicial=mensaje_inicial)

def handle_peticion_servicio(texto_usuario):
    texto_servicio_puro = texto_usuario.split('—')[0].strip()
    if session.get('modificando_cita'):
        return handle_modificar_servicio(texto_servicio_puro)
    nombres_servicios = session.get('nombres_servicios_disponibles', [])
    servicio_elegido = utils.encontrar_servicio_mas_cercano(texto_servicio_puro, nombres_servicios)
    if not servicio_elegido:
        servicios_db = database.listar_servicios(negocio_id=_get_negocio_id())
        botones_servicios = [f"{s['nombre']} — {s['precio']}€" for s in servicios_db]
        return {
            "respuesta": "No he entendido tu elección. Por favor, pulsa uno de los siguientes servicios:",
            "ui_component": { "type": "choice_buttons", "choices": botones_servicios },
            "nuevo_estado": "pidiendo_servicio"
        }
    session['servicio'] = servicio_elegido
    empleados = database.listar_empleados(negocio_id=_get_negocio_id())
    if not empleados:
        session['empleado_id'] = None
        session['empleado_nombre'] = None
        return _mostrar_calendario()
    session['empleados_disponibles'] = {e['nombre'].strip(): e['id'] for e in empleados}
    nombres_empleados = [e['nombre'].strip() for e in empleados]
    return {
        "respuesta": f"¡Perfecto, un '{servicio_elegido}'! ¿Con qué profesional te gustaría?",
        "ui_component": { "type": "choice_buttons", "choices": nombres_empleados },
        "nuevo_estado": "pidiendo_empleado"
    }

def handle_peticion_empleado(texto_usuario):
    empleado_elegido = texto_usuario.strip()
    empleados_map = session.get('empleados_disponibles', {})
    if empleado_elegido not in empleados_map:
        return {"respuesta": "No he reconocido a ese profesional.", "nuevo_estado": "pidiendo_empleado"}
    session['empleado_id'] = empleados_map[empleado_elegido]
    session['empleado_nombre'] = empleado_elegido
    return _mostrar_calendario()

def _mostrar_calendario():
    dias_disponibles = []
    hoy = utils.now_spain().date()
    dia_actual = hoy
    horario_semanal = database.obtener_horario_negocio(_get_negocio_id())
    dias_semana_map = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
    while dia_actual.month == hoy.month:
        nombre_columna_dia = f"horario_{dias_semana_map[dia_actual.weekday()]}"
        if horario_semanal and horario_semanal.get(nombre_columna_dia):
            dias_disponibles.append({
                "display": f"{utils.formato_nombre_dia_es(dia_actual)} {dia_actual.strftime('%d/%m')}",
                "value": dia_actual.strftime('%Y-%m-%d')
            })
        dia_actual += timedelta(days=1)
    return {
        "respuesta": "De acuerdo, elige un nuevo día del calendario:",
        "ui_component": { "type": "day_selector", "days": dias_disponibles },
        "nuevo_estado": "pidiendo_hora"
    }

def _get_horas_jornada_para_dia(dia_semana_num, negocio_id=None):
    id_del_negocio = negocio_id if negocio_id is not None else _get_negocio_id()
    if not id_del_negocio:
        return []

    horario_db = database.obtener_horario_negocio(id_del_negocio)
    if not horario_db:
        return []

    nombre_columna = f"horario_{dia_semana_num if isinstance(dia_semana_num, str) else ['lunes','martes','miercoles','jueves','viernes','sabado','domingo'][dia_semana_num]}"

    # Ajuste para mantener compatibilidad con tu estructura (dict-like)
    if isinstance(horario_db, dict):
        horas_str = horario_db.get(nombre_columna, "")
    else:
        horas_str = None
        try:
            horas_str = horario_db[nombre_columna]
        except Exception:
            horas_str = ""

    if not horas_str:
        return []

    return [h.strip() for h in horas_str.split(',')]

def _mostrar_horas_para_fecha(fecha_str):
    try:
        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        session['fecha'] = fecha_str
        horas_jornada = _get_horas_jornada_para_dia(fecha_obj.weekday())
        if not horas_jornada:
            return {"respuesta": f"Lo siento, el día {fecha_obj.strftime('%d/%m')} está cerrado.", "nuevo_estado": "pidiendo_hora"}

        # CORRECCIÓN del walrus: definir fuera y usar directamente
        horas_ocupadas = database.obtener_horas_ocupadas(
            fecha_str,
            negocio_id=_get_negocio_id(),
            empleado_id=session.get('empleado_id')
        )
        ahora = utils.now_spain()

        horas_libres = [
            h for h in horas_jornada
            if h not in horas_ocupadas
            and (
                fecha_obj > ahora.date()
                or (fecha_obj == ahora.date() and int(h.split(':')[0]) > ahora.hour)
            )
        ]

        nuevo_estado = 'modificar_confirmar_hora' if session.get('modificando_cita') else 'esperando_pre_confirmacion'
        empleado = session.get('empleado_nombre', 'el profesional seleccionado')
        if not horas_libres:
            return {"respuesta": f"Vaya, para el día {fecha_obj.strftime('%d/%m')} no quedan huecos con {empleado}.", "nuevo_estado": "pidiendo_hora"}

        return {
            "respuesta": f"Estupendo. Para el día {fecha_obj.strftime('%d/%m')} con {empleado}, tengo hueco en estas horas:",
            "ui_component": { "type": "hour_selector", "hours": horas_libres },
            "nuevo_estado": nuevo_estado
        }
    except (ValueError, IndexError):
        return {"respuesta": "No he entendido la fecha. Por favor, elige de nuevo.", "nuevo_estado": "pidiendo_hora"}

def handle_peticion_hora(texto_usuario):
    if session.get('modificando_cita'):
        return handle_modificar_fecha_hora(texto_usuario)
    return _mostrar_horas_para_fecha(texto_usuario)

def handle_esperando_pre_confirmacion(texto_usuario):
    hora_elegida = texto_usuario.strip()
    if not (':' in hora_elegida and len(hora_elegida) == 5):
        return {"respuesta": "Por favor, pulsa uno de los botones de hora.", "nuevo_estado": "esperando_pre_confirmacion"}
    session['hora'] = hora_elegida
    nombre_usuario = session.get('nombre', 'Cliente')
    fecha_legible = datetime.strptime(session.get('fecha'), '%Y-%m-%d').strftime('%A, %d de %B de %Y')
    empleado_nombre = session.get('empleado_nombre', 'el personal')
    resumen = (
        f"¡Perfecto, {nombre_usuario}! Vamos a revisar los datos:\n\n"
        f"› **Servicio:** {session.get('servicio')}\n"
        f"› **Profesional:** {empleado_nombre}\n"
        f"› **Día:** {fecha_legible}\n"
        f"› **Hora:** {session.get('hora')}\n\n"
        "¿Está todo correcto?"
    )
    botones_confirmacion = ["Confirmar Cita", "Cambiar Profesional", "Cambiar Día y Hora"]
    return {
        "respuesta": resumen,
        "ui_component": { "type": "choice_buttons", "choices": botones_confirmacion },
        "nuevo_estado": "procesando_confirmacion"
    }

def handle_procesando_confirmacion(texto_usuario):
    texto_norm = utils.normalizar_texto(texto_usuario)
    if "confirmar" in texto_norm:
        try:
            datos_para_guardar = {
                "nombre": session.get('nombre'),
                "telefono": session.get('telefono'),
                "servicio": session.get('servicio'),
                "fecha": session.get('fecha'),
                "hora": session.get('hora'),
                "empleado_id": session.get('empleado_id'),
                "email": session.get('email_cliente')  # <-- importante para upsert_cliente
            }
            database.guardar_reserva(datos_para_guardar, _get_negocio_id())

            negocio_info = database.obtener_negocio_por_id(_get_negocio_id())
            datos_notificacion = {
                **datos_para_guardar,
                "empleado_nombre": session.get('empleado_nombre'),
                "negocio_nombre": _get_negocio_nombre(),
                "email_negocio": negocio_info.get('email') if negocio_info else None,
                "email_cliente": session.get('email_cliente')
            }
            email_manager.enviar_notificacion_cita(datos_notificacion)

            respuesta_final = "¡Tachán! Cita confirmada. Te hemos enviado un email con todos los detalles. ¡Gracias!"
            _limpiar_sesion_conversacion()
            nuevo_mensaje_bienvenida = handle_bienvenida("")
            return {
                "respuesta": respuesta_final,
                "post_respuesta": nuevo_mensaje_bienvenida,
                "nuevo_estado": "esperando_eleccion_inicial"
            }
        except Exception as e:
            print(f"!!! ERROR al guardar o notificar cita: {e}")
            return {"respuesta": "¡Uy! Ha ocurrido un error al confirmar tu cita.", "nuevo_estado": None}
    elif "profesional" in texto_norm:
        empleados = database.listar_empleados(negocio_id=_get_negocio_id())
        nombres_empleados = [e['nombre'].strip() for e in empleados]
        return {
            "respuesta": "¡Entendido! Elige de nuevo con qué profesional te gustaría:",
            "ui_component": { "type": "choice_buttons", "choices": nombres_empleados },
            "nuevo_estado": "pidiendo_empleado"
        }
    elif "dia" in texto_norm or "hora" in texto_norm:
        return _mostrar_calendario()
    else:
        return {"respuesta": "No te he entendido. Por favor, elige una de las opciones.", "nuevo_estado": "procesando_confirmacion"}

def handle_gestion_pide_telefono(texto_usuario):
    telefono = texto_usuario.strip()
    session['telefono'] = telefono  # guardar para notificaciones posteriores
    # Recuperar email previo si existe soporte (tabla clientes)
    try:
        prev = database.obtener_email_cliente(telefono, _get_negocio_id())
        if prev:
            session['email_cliente'] = prev
    except Exception:
        pass

    citas_encontradas = database.obtener_citas_futuras_por_telefono(telefono, negocio_id=_get_negocio_id())
    citas_futuras_reales = [c for c in citas_encontradas if not utils.ha_pasado_fecha_hora(c['fecha'], c['hora'])]
    if not citas_futuras_reales:
        return {"respuesta": "No he encontrado ninguna cita gestionable con ese teléfono.", "nuevo_estado": "gestion_pide_telefono"}
    cita = citas_futuras_reales[0]
    cita_serializable = {
        "id": cita['id'],
        "fecha": cita['fecha'].strftime('%Y-%m-%d'),
        "hora": cita['hora'].strftime('%H:%M'),
        "servicio_nombre": cita['servicio_nombre'],
        "empleado_nombre": cita.get('empleado_nombre', 'No asignado')
    }
    session['cita_a_gestionar'] = cita_serializable
    fecha_legible = cita['fecha'].strftime('%A, %d de %B'); hora_legible = cita['hora'].strftime('%H:%M')
    mensaje_intro = f"He encontrado tu cita para un **'{cita['servicio_nombre']}'** con **{cita_serializable['empleado_nombre']}** el **{fecha_legible} a las {hora_legible}**."
    return {
        "respuesta": f"{mensaje_intro}\n\n¿Qué quieres hacer?",
        "ui_component": { "type": "choice_buttons", "choices": ["Modificar Cita", "Cancelar Cita"] },
        "nuevo_estado": "gestion_esperando_accion"
    }

def handle_gestion_esperando_accion(texto_usuario):
    texto_norm = utils.normalizar_texto(texto_usuario)
    if "modificar" in texto_norm:
        return {
            "respuesta": "¿Qué te gustaría cambiar?",
            "ui_component": { "type": "choice_buttons", "choices": ["El Servicio", "El Día y la Hora"] },
            "nuevo_estado": "gestion_pide_campo_a_modificar"
        }
    elif "cancelar" in texto_norm:
        return {
            "respuesta": "¿Estás seguro de que quieres cancelarla?",
            "ui_component": { "type": "choice_buttons", "choices": ["Sí, cancelar", "No, mantener"] },
            "nuevo_estado": "gestion_confirmar_cancelacion"
        }
    else:
        return {"respuesta": "No te he entendido. Elige 'Modificar' o 'Cancelar'.", "nuevo_estado": "gestion_esperando_accion"}

def handle_gestion_confirmar_cancelacion(texto_usuario):
    respuesta_norm = utils.normalizar_texto(texto_usuario)
    if 'si' in respuesta_norm:
        cita_a_cancelar = session.get('cita_a_gestionar')
        if cita_a_cancelar:
            # database.cancelar_cita devuelve el detalle previo de la cita
            detalle_prev = database.cancelar_cita(cita_a_cancelar['id'], negocio_id=_get_negocio_id())
            try:
                if detalle_prev:
                    datos_email = {
                        "tipo": "cancelacion",
                        "negocio_nombre": _get_negocio_nombre(),
                        "email_negocio": detalle_prev.get('negocio_email'),
                        "email_cliente": session.get('email_cliente'),  # puede ser None si no lo tenemos persistido
                        "nombre": detalle_prev.get('nombre_cliente'),
                        "telefono": detalle_prev.get('telefono'),
                        "servicio": detalle_prev.get('servicio_nombre'),
                        "empleado_nombre": detalle_prev.get('empleado_nombre'),
                        "fecha": detalle_prev.get('fecha').strftime('%Y-%m-%d') if detalle_prev.get('fecha') else None,
                        "hora": detalle_prev.get('hora').strftime('%H:%M') if detalle_prev.get('hora') else None
                    }
                    email_manager.enviar_notificacion_cancelacion(datos_email)
            except Exception as e:
                print(f"!!! ERROR al enviar email de cancelación: {e}")
        _limpiar_sesion_conversacion()
        return {"respuesta": "¡Hecho! Tu cita ha sido cancelada.", "nuevo_estado": "esperando_eleccion_inicial"}
    elif 'no' in respuesta_norm:
        _limpiar_sesion_conversacion()
        return {"respuesta": "De acuerdo. No he cancelado tu cita.", "nuevo_estado": "esperando_eleccion_inicial"}
    else:
        return {
            "respuesta": "No te he entendido. Por favor, pulsa una de las opciones.",
            "ui_component": { "type": "choice_buttons", "choices": ["Sí, cancelar", "No, mantener"] },
            "nuevo_estado": "gestion_confirmar_cancelacion"
        }

def handle_gestion_pide_campo_a_modificar(texto_usuario):
    texto_norm = utils.normalizar_texto(texto_usuario)
    session['modificando_cita'] = True
    if 'servicio' in texto_norm:
        servicios_db = database.listar_servicios(negocio_id=_get_negocio_id())
        nombres_servicios = [s['nombre'] for s in servicios_db]
        session['nombres_servicios_disponibles'] = nombres_servicios
        botones_servicios = [f"{s['nombre']} — {s['precio']}€" for s in servicios_db]
        return {
            "respuesta": "Entendido. ¿Por cuál de estos servicios quieres cambiarla?",
            "ui_component": { "type": "choice_buttons", "choices": botones_servicios },
            "nuevo_estado": "pidiendo_servicio"
        }
    elif 'dia' in texto_norm or 'hora' in texto_norm:
        return _mostrar_calendario()
    else:
        return {"respuesta": "No te he entendido. Elige una de las opciones.", "nuevo_estado": "gestion_pide_campo_a_modificar"}

def handle_modificar_servicio(texto_usuario_puro):
    nombres_servicios = session.get('nombres_servicios_disponibles', [])
    nuevo_servicio = utils.encontrar_servicio_mas_cercano(texto_usuario_puro, nombres_servicios)
    if not nuevo_servicio:
        return {"respuesta": "No he reconocido ese servicio.", "nuevo_estado": "pidiendo_servicio"}
    cita_id = session['cita_a_gestionar']['id']
    # Obtener antes/después para notificación
    antes, despues = database.modificar_cita(cita_id, _get_negocio_id(), {'servicio': nuevo_servicio})
    try:
        if antes and despues:
            datos_email = {
                "tipo": "modificacion",
                "negocio_nombre": _get_negocio_nombre(),
                "email_negocio": database.obtener_email_negocio(_get_negocio_id()),
                "email_cliente": session.get('email_cliente'),
                "nombre": antes.get('nombre_cliente'),
                "telefono": antes.get('telefono'),
                "servicio_antes": antes.get('servicio_nombre'),
                "servicio_despues": despues.get('servicio_nombre'),
                "empleado_nombre": despues.get('empleado_nombre'),
                "fecha": (despues.get('fecha').strftime('%Y-%m-%d') if despues.get('fecha') else None),
                "hora": (despues.get('hora').strftime('%H:%M') if despues.get('hora') else None)
            }
            email_manager.enviar_notificacion_modificacion(datos_email)
    except Exception as e:
        print(f"!!! ERROR al enviar email de modificación (servicio): {e}")

    _limpiar_sesion_conversacion()
    return {"respuesta": f"¡Listo! He cambiado el servicio de tu cita a **'{nuevo_servicio}'**. El día y la hora se mantienen.", "nuevo_estado": "esperando_eleccion_inicial"}

def handle_modificar_fecha_hora(texto_usuario):
    return _mostrar_horas_para_fecha(texto_usuario)

def handle_modificar_confirmar_hora(texto_usuario):
    hora_elegida = texto_usuario.strip()
    if not (':' in hora_elegida and len(hora_elegida) == 5):
        return {"respuesta": "Por favor, pulsa uno de los botones de hora.", "nuevo_estado": "modificar_confirmar_hora"}
    cita_id = session['cita_a_gestionar']['id']
    nuevos_datos = { 'fecha': session.get('fecha'), 'hora': hora_elegida }
    antes, despues = database.modificar_cita(cita_id, _get_negocio_id(), nuevos_datos)

    try:
        if antes and despues:
            datos_email = {
                "tipo": "modificacion",
                "negocio_nombre": _get_negocio_nombre(),
                "email_negocio": database.obtener_email_negocio(_get_negocio_id()),
                "email_cliente": session.get('email_cliente'),
                "nombre": antes.get('nombre_cliente'),
                "telefono": antes.get('telefono'),
                "servicio_antes": antes.get('servicio_nombre'),
                "servicio_despues": despues.get('servicio_nombre'),
                "empleado_nombre": despues.get('empleado_nombre'),
                "fecha": (despues.get('fecha').strftime('%Y-%m-%d') if despues.get('fecha') else None),
                "hora": (despues.get('hora').strftime('%H:%M') if despues.get('hora') else None)
            }
            email_manager.enviar_notificacion_modificacion(datos_email)
    except Exception as e:
        print(f"!!! ERROR al enviar email de modificación (fecha/hora): {e}")

    _limpiar_sesion_conversacion()
    fecha_legible = datetime.strptime(nuevos_datos['fecha'], '%Y-%m-%d').strftime('%d/%m/%Y')
    return {"respuesta": f"¡Cita actualizada! Tu nueva cita es el **{fecha_legible} a las {hora_elegida}**.", "nuevo_estado": "esperando_eleccion_inicial"}
