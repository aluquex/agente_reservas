# app.py
from flask import Flask, request, jsonify, session, render_template, flash, redirect, url_for, send_from_directory, Response
from flask_cors import CORS
import config
import handlers
import utils
import database
import email_manager
import os
import io
import csv
from datetime import datetime, timedelta, date
import locale
import threading
import time

# ---------- Locale español (si está disponible) ----------
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'esp')
    except locale.Error:
        print("Advertencia: No se pudo establecer el locale en español en app.py.")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = getattr(config, "SECRET_KEY", "dev-secret")

CORS(app, resources={r"/mensaje": {"origins": list(getattr(config, "CORS_ALLOWED_ORIGINS", ["*"]))}}, supports_credentials=True)

REINICIO_KEYWORDS = ['empezar', 'iniciar', 'volver', 'atras', 'reinicio', 'inicio', 'menu', 'reset']
ESTADO_HANDLERS = {
    'esperando_eleccion_inicial': handlers.handle_eleccion_inicial,
    'pidiendo_nombre': handlers.handle_peticion_nombre,
    'pidiendo_telefono': handlers.handle_peticion_telefono,
    'pidiendo_email': handlers.handle_peticion_email,
    'pidiendo_servicio': handlers.handle_peticion_servicio,
    'pidiendo_empleado': handlers.handle_peticion_empleado,
    'pidiendo_hora': handlers.handle_peticion_hora,
    'esperando_pre_confirmacion': handlers.handle_esperando_pre_confirmacion,
    'procesando_confirmacion': handlers.handle_procesando_confirmacion,
    'gestion_pide_telefono': handlers.handle_gestion_pide_telefono,
    'gestion_esperando_accion': handlers.handle_gestion_esperando_accion,
    'gestion_confirmar_cancelacion': handlers.handle_gestion_confirmar_cancelacion,
    'gestion_pide_campo_a_modificar': handlers.handle_gestion_pide_campo_a_modificar,
    'modificar_confirmar_hora': handlers.handle_modificar_confirmar_hora,
}

# =====================================================
# Chat del bot
# =====================================================
@app.route("/mensaje", methods=["POST"])
def mensaje():
    negocio = None
    slug_negocio_url = request.args.get("business")
    
    if slug_negocio_url or 'negocio_id' not in session:
        session.clear()
        if slug_negocio_url:
            slug_limpio = slug_negocio_url.strip().lower()
            negocio = database.obtener_negocio_por_slug(slug_limpio)
        if not negocio:
            todos_los_negocios = database.listar_negocios()
            if todos_los_negocios:
                primer_negocio_id = todos_los_negocios[0]['id']
                negocio = database.obtener_negocio_por_id(primer_negocio_id)
    else:
        negocio = database.obtener_negocio_por_id(session['negocio_id'])

    if not negocio:
        return jsonify({"respuesta": "Error: No se pudo cargar ningún negocio válido."})

    session['negocio_id'] = negocio['id']
    session['business_slug'] = negocio['slug']
    session['negocio_nombre'] = negocio['nombre']
    
    texto_usuario = request.json.get("mensaje", "").strip()
    texto_normalizado = utils.normalizar_texto(texto_usuario)
    estado_actual = session.get('estado')

    if any(keyword in texto_normalizado for keyword in REINICIO_KEYWORDS):
        respuesta_dict = handlers.handle_bienvenida(texto_usuario)
    else:
        handler_func = ESTADO_HANDLERS.get(estado_actual)
        if handler_func:
            respuesta_dict = handler_func(texto_usuario)
        else:
            respuesta_dict = handlers.handle_bienvenida(texto_usuario)

    if not respuesta_dict.get("respuesta"):
        respuesta_dict = {"respuesta": "Lo siento, no te he entendido."}
    
    if 'nuevo_estado' in respuesta_dict:
        session['estado'] = respuesta_dict.pop('nuevo_estado')
        
    return jsonify(respuesta_dict)

# =====================================================
# Estáticos
# =====================================================
@app.route("/index.html")
def servir_index():
    return send_from_directory(os.getcwd(), "index.html")

# =====================================================
# Admin básico
# =====================================================
@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    password_ingresada = request.args.get('password')
    if password_ingresada != getattr(config, "ADMIN_PASSWORD", ""):
        return "Acceso denegado.", 403
    if request.method == 'POST':
        try:
            datos_negocio = {
                'nombre': request.form['nombre'],
                'slug': request.form['slug'],
                'direccion': request.form.get('direccion'),
                'telefono': request.form.get('telefono'),
                'email': request.form.get('email'),
                'servicios': [],
                'empleados': []
            }
            i = 0
            while f'servicio_nombre_{i}' in request.form:
                nombre = request.form[f'servicio_nombre_{i}']
                precio = request.form[f'servicio_precio_{i}']
                duracion = request.form[f'servicio_duracion_{i}']
                if nombre and precio and duracion:
                    datos_negocio['servicios'].append({
                        'nombre': nombre, 'precio': float(precio), 'duracion': int(duracion)
                    })
                i += 1
            i = 0
            while f'empleado_nombre_{i}' in request.form:
                nombre = request.form[f'empleado_nombre_{i}']
                if nombre:
                    datos_negocio['empleados'].append({'nombre': nombre})
                i += 1
            database.crear_negocio_completo(datos_negocio)
            flash(f"¡Negocio '{datos_negocio['nombre']}' creado con éxito!", 'success')
        except Exception as e:
            print(f"Error al crear negocio: {e}")
            flash(f"Error al crear el negocio: {e}", 'error')
        return redirect(url_for('admin_panel', password=password_ingresada))
    return render_template('admin.html', password=password_ingresada)

@app.route("/admin/negocios")
def lista_negocios_ruta():
    password_ingresada = request.args.get('password')
    if password_ingresada != getattr(config, "ADMIN_PASSWORD", ""):
        return "Acceso denegado.", 403
    filtro = request.args.get('filtro_nombre', '')
    negocios_existentes = database.listar_negocios(filtro)
    return render_template('lista_negocios.html', negocios=negocios_existentes, password=password_ingresada)

@app.route("/debug-negocios")
def debug_negocios():
    password_ingresada = request.args.get('password')
    if password_ingresada != getattr(config, "ADMIN_PASSWORD", ""):
        return "Acceso denegado.", 403
    todos_los_negocios = database.listar_negocios()
    html_respuesta = "<h1>Contenido Real de la Tabla 'negocios'</h1><table border='1'><tr><th>ID</th><th>Nombre</th><th>Slug</th></tr>"
    for negocio in todos_los_negocios:
        html_respuesta += f"<tr><td>{negocio['id']}</td><td>{negocio['nombre']}</td><td>{negocio['slug']}</td></tr>"
    html_respuesta += "</table>"
    return html_respuesta

@app.route("/debug-citas/<int:negocio_id>")
def debug_citas(negocio_id):
    password_ingresada = request.args.get('password')
    if password_ingresada != getattr(config, "ADMIN_PASSWORD", ""):
        return "Acceso denegado.", 403
    todas_las_citas = database.obtener_todas_las_citas(negocio_id)
    html_respuesta = f"<h1>Contenido Real de la Tabla 'citas' para Negocio ID: {negocio_id}</h1><table border='1'><tr><th>Fecha</th><th>Hora</th><th>Cliente</th><th>Teléfono</th></tr>"
    for cita in todas_las_citas:
        html_respuesta += f"<tr><td>{cita['fecha']}</td><td>{cita['hora']}</td><td>{cita['nombre_cliente']}</td><td>{cita['telefono']}</td></tr>"
    html_respuesta += "</table>"
    return html_respuesta

@app.route("/admin/borrar/<int:negocio_id>", methods=["POST"])
def borrar_negocio_ruta(negocio_id):
    password_ingresada = request.args.get('password')
    if password_ingresada != getattr(config, "ADMIN_PASSWORD", ""):
        return "Acceso denegado.", 403
    try:
        database.borrar_negocio(negocio_id)
        flash(f"Negocio ID {negocio_id} borrado con éxito.", 'success')
    except Exception as e:
        print(f"Error al borrar negocio: {e}")
        flash(f"Error al borrar negocio ID {negocio_id}: {e}", 'error')
    return redirect(url_for('lista_negocios_ruta', password=password_ingresada))

@app.route("/admin/editar/<int:negocio_id>", methods=["GET", "POST"])
def editar_negocio_ruta(negocio_id):
    password_ingresada = request.args.get('password')
    if password_ingresada != getattr(config, "ADMIN_PASSWORD", ""):
        return "Acceso denegado.", 403
    if request.method == 'POST':
        try:
            datos_negocio = {
                'nombre': request.form['nombre'],
                'slug': request.form['slug'],
                'direccion': request.form.get('direccion'),
                'telefono': request.form.get('telefono'),
                'email': request.form.get('email'),
                'servicios': [],
                'empleados': [],
                'horario_lunes': request.form.get('horario_lunes'),
                'horario_martes': request.form.get('horario_martes'),
                'horario_miercoles': request.form.get('horario_miercoles'),
                'horario_jueves': request.form.get('horario_jueves'),
                'horario_viernes': request.form.get('horario_viernes'),
                'horario_sabado': request.form.get('horario_sabado'),
                'horario_domingo': request.form.get('horario_domingo')
            }
            i = 0
            while f'servicio_nombre_{i}' in request.form:
                nombre = request.form[f'servicio_nombre_{i}']
                precio = request.form[f'servicio_precio_{i}']
                duracion = request.form[f'servicio_duracion_{i}']
                if nombre and precio and duracion:
                    datos_negocio['servicios'].append({
                        'nombre': nombre, 'precio': float(precio), 'duracion': int(duracion)
                    })
                i += 1
            i = 0
            while f'empleado_nombre_{i}' in request.form:
                nombre = request.form[f'empleado_nombre_{i}']
                if nombre:
                    datos_negocio['empleados'].append({'nombre': nombre})
                i += 1
            database.modificar_negocio_completo(negocio_id, datos_negocio)
            flash(f"Negocio '{datos_negocio['nombre']}' actualizado con éxito.", 'success')
        except Exception as e:
            print(f"Error al modificar negocio: {e}")
            flash(f"Error al modificar negocio: {e}", 'error')
        return redirect(url_for('lista_negocios_ruta', password=password_ingresada))
    negocio_a_editar = database.obtener_negocio_por_id(negocio_id)
    return render_template('editar_negocio.html', negocio=negocio_a_editar, password=password_ingresada)

# =====================================================
# Export CSV
# =====================================================
@app.route("/admin/exportar_citas/<int:negocio_id>")
def exportar_citas_csv(negocio_id):
    password_ingresada = request.args.get('password')
    if password_ingresada != getattr(config, "ADMIN_PASSWORD", ""):
        return "Acceso denegado.", 403
    hoy = datetime.now()
    inicio_mes = hoy.replace(day=1).date()
    fin_mes_temp = (hoy.replace(day=28) + timedelta(days=4)).replace(day=1)
    fin_mes = (fin_mes_temp - timedelta(days=1)).date()
    citas = database.obtener_citas_para_exportar(negocio_id, inicio_mes, fin_mes)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Fecha', 'Hora', 'Cliente', 'Telefono', 'Servicio', 'Profesional', 'Precio'])
    for cita in citas:
        hora_formateada = cita['hora'].strftime('%H:%M') if cita['hora'] else ''
        writer.writerow([
            cita['fecha'],
            hora_formateada,
            cita['nombre_cliente'],
            cita['telefono'],
            cita['servicio_nombre'],
            cita['empleado_nombre'] or 'No asignado',
            cita['precio']
        ])
    csv_final = output.getvalue().encode('utf-8-sig')
    return Response(
        csv_final,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=citas_{negocio_id}_{hoy.strftime('%Y-%m')}.csv"}
    )

# =====================================================
# Panel del cliente (AGENDA)
# =====================================================
@app.route("/cliente/panel/<int:negocio_id>")
def panel_cliente(negocio_id):
    negocio = database.obtener_negocio_por_id(negocio_id)
    if not negocio:
        return "Negocio no encontrado", 404
    
    fecha_str = request.args.get('fecha', default=date.today().isoformat())
    try:
        fecha_obj = date.fromisoformat(fecha_str)
    except ValueError:
        fecha_obj = date.today()

    horas_jornada = handlers._get_horas_jornada_para_dia(fecha_obj.weekday(), negocio_id=negocio_id)
    citas_del_dia = database.obtener_citas_del_dia(negocio_id, fecha_obj)

    grupos = {}
    for c in citas_del_dia:
        hhmm = c['hora'].strftime('%H:%M')
        grupos.setdefault(hhmm, []).append({
            "id": c['id'],
            "nombre_cliente": c['nombre_cliente'],
            "servicio_nombre": c['servicio_nombre'],
            "empleado_nombre": c.get('empleado_nombre') or 'No asignado'
        })

    agenda_completa = []
    for hora in horas_jornada:
        lista = grupos.get(hora, [])
        if lista:
            agenda_completa.append({'hora': hora, 'status': 'ocupada', 'citas': lista})
        else:
            agenda_completa.append({'hora': hora, 'status': 'disponible', 'citas': []})
    
    return render_template(
        'cliente_panel.html',
        negocio=negocio,
        agenda=agenda_completa,
        fecha_seleccionada=fecha_obj,
        ADMIN_PASSWORD=getattr(config, "ADMIN_PASSWORD", "")
    )

# =====================================================
# Cancelación desde panel — notifica negocio + cliente
# =====================================================
@app.route("/cliente/citas/cancelar/<int:cita_id>/<int:negocio_id>", methods=["POST"])
def cliente_cancelar_cita(cita_id, negocio_id):
    try:
        detalle_prev = database.cancelar_cita(cita_id, negocio_id)
        if detalle_prev:
            try:
                email_cliente = database.obtener_email_cliente(detalle_prev.get('telefono'), negocio_id)
            except Exception:
                email_cliente = None

            datos_email = {
                "negocio_nombre": detalle_prev.get('negocio_nombre'),
                "negocio_slug": detalle_prev.get('negocio_slug'),
                "email_negocio": detalle_prev.get('negocio_email') or database.obtener_email_negocio(negocio_id),
                "email_cliente": email_cliente,
                "nombre": detalle_prev.get('nombre_cliente'),
                "telefono": detalle_prev.get('telefono'),
                "servicio": detalle_prev.get('servicio_nombre'),
                "empleado_nombre": detalle_prev.get('empleado_nombre'),
                "fecha": detalle_prev.get('fecha').strftime('%Y-%m-%d') if detalle_prev.get('fecha') else None,
                "hora": detalle_prev.get('hora').strftime('%H:%M') if detalle_prev.get('hora') else None,
                "direccion": detalle_prev.get('direccion'),
                "cita_id": detalle_prev.get('id'),
                "negocio_id": negocio_id,
            }
            email_manager.enviar_notificacion_cancelacion(datos_email)
            flash("La cita ha sido cancelada con éxito.", "success")
        else:
            flash("No se encontró la cita o ya había sido cancelada.", "error")
    except Exception as e:
        print(f"Error al cancelar cita desde panel cliente: {e}")
        flash("Hubo un error al intentar cancelar la cita.", "error")
    
    fecha_a_redirigir = request.form.get('fecha_actual', date.today().isoformat())
    return redirect(url_for('panel_cliente', negocio_id=negocio_id, fecha=fecha_a_redirigir))

# =====================================================
# Gestión de disponibilidad
# =====================================================
@app.route("/cliente/panel/<int:negocio_id>/disponibilidad", methods=['GET', 'POST'])
def gestion_disponibilidad(negocio_id):
    negocio = database.obtener_negocio_por_id(negocio_id)
    if not negocio:
        return "Negocio no encontrado", 404

    fecha_str = request.args.get('fecha', default=date.today().isoformat())
    try:
        fecha_obj = date.fromisoformat(fecha_str)
    except ValueError:
        fecha_obj = date.today()

    if request.method == 'POST':
        horas_bloqueadas_form = request.form.getlist('horas_bloqueadas')
        horas_jornada = handlers._get_horas_jornada_para_dia(fecha_obj.weekday(), negocio_id=negocio_id)
        for hora in horas_jornada:
            database.eliminar_bloqueo(negocio_id, fecha_obj, hora)
        for hora_str in horas_bloqueadas_form:
            database.crear_bloqueo(negocio_id, fecha_obj, hora_str)
        flash('Disponibilidad actualizada correctamente.', 'success')
        return redirect(url_for('gestion_disponibilidad', negocio_id=negocio_id, fecha=fecha_obj.isoformat()))

    horas_jornada = handlers._get_horas_jornada_para_dia(fecha_obj.weekday(), negocio_id=negocio_id)
    citas_del_dia = database.obtener_citas_del_dia(negocio_id, fecha_obj)
    bloqueos_del_dia = database.obtener_horas_bloqueadas(negocio_id, fecha_obj)

    horas_ocupadas = {cita['hora'].strftime('%H:%M') for cita in citas_del_dia}
    horas_bloqueadas = {bloqueo['hora'].strftime('%H:%M') for bloqueo in bloqueos_del_dia}
    
    estado_horas = []
    for hora in horas_jornada:
        status = 'disponible'
        if hora in horas_ocupadas:
            status = 'ocupada'
        elif hora in horas_bloqueadas:
            status = 'bloqueada'
        estado_horas.append({'hora': hora, 'status': status})

    return render_template(
        'disponibilidad.html',
        negocio=negocio,
        fecha_seleccionada=fecha_obj,
        estado_horas=estado_horas
    )

# =====================================================
# Recordatorios 2h antes (email + WhatsApp) — Scheduler
# =====================================================
REMINDERS_ENABLED = getattr(config, "REMINDERS_ENABLED", True)

_scheduler_started = False
def _scheduler_loop():
    print("[Scheduler] Recordatorios 2h: iniciado.")
    try:
        database.ensure_tabla_recordatorios()
    except Exception as e:
        print(f"[Scheduler] Error creando tabla recordatorios: {e}")
    while True:
        try:
            ahora = utils.now_spain() if hasattr(utils, "now_spain") else datetime.now()

            # Ventana robusta: 2h por delante, centrada en la hora en punto ±5 min
            base = ahora.replace(minute=0, second=0, microsecond=0) + timedelta(hours=2)
            desde = base - timedelta(minutes=5)
            hasta = base + timedelta(minutes=5)

            citas = database.obtener_citas_para_recordatorio_2h(desde, hasta)
            if citas:
                print(f"[Scheduler] Ventana {desde}..{hasta} -> {len(citas)} cita(s)")

            for c in citas:
                datos = {
                    "negocio_id": c["negocio_id"],
                    "negocio_nombre": c["negocio_nombre"],
                    "negocio_slug": c.get("negocio_slug"),
                    "email_negocio": c.get("negocio_email"),
                    "email_cliente": c.get("cliente_email"),
                    "direccion": c.get("direccion"),
                    "cita_id": c["id"],
                    "nombre": c["nombre_cliente"],
                    "telefono": c["telefono"],
                    "servicio": c.get("servicio_nombre"),
                    "empleado_nombre": c.get("empleado_nombre") or "No asignado",
                    "fecha": c["fecha"].strftime("%Y-%m-%d"),
                    "hora": c["hora"].strftime("%H:%M"),
                }
                try:
                    email_manager.enviar_recordatorio_cita(datos)
                    print(f"[Scheduler] Email recordatorio enviado (cita {c['id']})")
                except Exception as e:
                    print(f"[Scheduler] Error email recordatorio {c['id']}: {e}")
                try:
                    import whatsapp_manager
                    whatsapp_manager.enviar_recordatorio_whatsapp(datos)
                    print(f"[Scheduler] WhatsApp recordatorio enviado (cita {c['id']})")
                except Exception as e:
                    # Silenciar si no está configurado Twilio
                    print(f"[Scheduler] WhatsApp no enviado (cita {c['id']}): {e}")
                try:
                    database.marcar_recordatorio_enviado(c["id"], "2h")
                except Exception as e:
                    print(f"[Scheduler] Error marcando recordatorio {c['id']}: {e}")
        except Exception as e:
            print(f"[Scheduler] Error ciclo: {e}")
        time.sleep(60)

# Flask 3.x: no existe before_first_request. Arrancamos el scheduler la primera vez que llega cualquier request.
@app.before_request
def _start_scheduler_once():
    global _scheduler_started
    if REMINDERS_ENABLED and not _scheduler_started:
        _scheduler_started = True
        t = threading.Thread(target=_scheduler_loop, daemon=True)
        t.start()

# =====================================================
# Otros
# =====================================================
@app.route("/politica-privacidad")
def politica_privacidad():
    return render_template('politica_privacidad.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(getattr(config, "FLASK_PORT", 5001)), debug=True)
