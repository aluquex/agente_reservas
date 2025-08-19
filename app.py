# app.py
from flask import Flask, request, jsonify, session, render_template, flash, redirect, url_for, send_from_directory
from flask_cors import CORS
import config
import handlers
import utils
import database
import os

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

CORS(app, resources={r"/mensaje": {"origins": list(config.CORS_ALLOWED_ORIGINS)}}, supports_credentials=True)

# --- CORRECCIÓN DE SINTAXIS ---
REINICIO_KEYWORDS = ['empezar', 'iniciar', 'volver', 'atras', 'reinicio', 'inicio', 'menu', 'reset']

ESTADO_HANDLERS = {
    'esperando_eleccion_inicial': handlers.handle_eleccion_inicial,
    'pidiendo_nombre': handlers.handle_peticion_nombre,
    'pidiendo_telefono': handlers.handle_peticion_telefono,
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

@app.route("/mensaje", methods=["POST"])
def mensaje():
    print(f"--- DEBUG: URL COMPLETA RECIBIDA POR EL BACKEND: {request.url} ---")
    
    negocio = None
    slug_negocio_url = request.args.get("business")
    texto_usuario = request.json.get("mensaje", "").strip()
    texto_normalizado = utils.normalizar_texto(texto_usuario)
    
    if slug_negocio_url:
        session.pop('estado', None)
        slug_limpio = slug_negocio_url.strip().lower()
        negocio = database.obtener_negocio_por_slug(slug_limpio)
        if negocio:
            session['negocio_id'] = negocio['id']
    
    elif 'negocio_id' in session:
        negocio = database.obtener_negocio_por_id(session['negocio_id'])

    if not negocio:
        session.pop('estado', None)
        todos_los_negocios = database.listar_negocios()
        if todos_los_negocios:
            primer_negocio_id = todos_los_negocios[0]['id']
            negocio = database.obtener_negocio_por_id(primer_negocio_id)
            session['negocio_id'] = primer_negocio_id

    if not negocio:
        return jsonify({"respuesta": "Error: No se pudo cargar ningún negocio válido."})

    session['business_slug'] = negocio['slug']
    session['negocio_nombre'] = negocio['nombre']
    
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

# ... (el resto del archivo es idéntico)
@app.route("/index.html")
def servir_index():
    return send_from_directory(os.getcwd(), "index.html")
@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    password_ingresada = request.args.get('password')
    if password_ingresada != config.ADMIN_PASSWORD: return "Acceso denegado.", 403
    if request.method == 'POST':
        try:
            datos_negocio = { 'nombre': request.form['nombre'], 'slug': request.form['slug'], 'direccion': request.form.get('direccion'), 'telefono': request.form.get('telefono'), 'email': request.form.get('email'), 'servicios': [], 'empleados': [] }
            i = 0
            while f'servicio_nombre_{i}' in request.form:
                nombre = request.form[f'servicio_nombre_{i}']; precio = request.form[f'servicio_precio_{i}']; duracion = request.form[f'servicio_duracion_{i}']
                if nombre and precio and duracion: datos_negocio['servicios'].append({ 'nombre': nombre, 'precio': float(precio), 'duracion': int(duracion) })
                i += 1
            i = 0
            while f'empleado_nombre_{i}' in request.form:
                nombre = request.form[f'empleado_nombre_{i}']
                if nombre: datos_negocio['empleados'].append({'nombre': nombre})
                i += 1
            database.crear_negocio_completo(datos_negocio)
            flash(f"¡Negocio '{datos_negocio['nombre']}' creado con éxito!", 'success')
        except Exception as e:
            print(f"Error al crear negocio: {e}"); flash(f"Error al crear el negocio: {e}", 'error')
        return redirect(url_for('admin_panel', password=password_ingresada))
    return render_template('admin.html', password=password_ingresada)
@app.route("/admin/negocios")
def lista_negocios_ruta():
    password_ingresada = request.args.get('password')
    if password_ingresada != config.ADMIN_PASSWORD: return "Acceso denegado.", 403
    filtro = request.args.get('filtro_nombre', '')
    negocios_existentes = database.listar_negocios(filtro)
    return render_template('lista_negocios.html', negocios=negocios_existentes, password=password_ingresada)
@app.route("/debug-negocios")
def debug_negocios():
    password_ingresada = request.args.get('password')
    if password_ingresada != config.ADMIN_PASSWORD: return "Acceso denegado.", 403
    todos_los_negocios = database.listar_negocios()
    html_respuesta = "<h1>Contenido Real de la Tabla 'negocios'</h1><table border='1'><tr><th>ID</th><th>Nombre</th><th>Slug</th></tr>"
    for negocio in todos_los_negocios: html_respuesta += f"<tr><td>{negocio['id']}</td><td>{negocio['nombre']}</td><td>{negocio['slug']}</td></tr>"
    html_respuesta += "</table>"
    return html_respuesta
@app.route("/admin/borrar/<int:negocio_id>", methods=["POST"])
def borrar_negocio_ruta(negocio_id):
    password_ingresada = request.args.get('password')
    if password_ingresada != config.ADMIN_PASSWORD: return "Acceso denegado.", 403
    try:
        database.borrar_negocio(negocio_id)
        flash(f"Negocio ID {negocio_id} borrado con éxito.", 'success')
    except Exception as e:
        print(f"Error al borrar negocio: {e}"); flash(f"Error al borrar negocio ID {negocio_id}: {e}", 'error')
    return redirect(url_for('lista_negocios_ruta', password=password_ingresada))
@app.route("/admin/editar/<int:negocio_id>", methods=["GET", "POST"])
def editar_negocio_ruta(negocio_id):
    password_ingresada = request.args.get('password')
    if password_ingresada != config.ADMIN_PASSWORD: return "Acceso denegado.", 403
    if request.method == 'POST':
        try:
            datos_negocio = { 'nombre': request.form['nombre'], 'slug': request.form['slug'], 'direccion': request.form.get('direccion'), 'telefono': request.form.get('telefono'), 'email': request.form.get('email'), 'servicios': [], 'empleados': [], 'horario_lunes': request.form.get('horario_lunes'), 'horario_martes': request.form.get('horario_martes'), 'horario_miercoles': request.form.get('horario_miercoles'), 'horario_jueves': request.form.get('horario_jueves'), 'horario_viernes': request.form.get('horario_viernes'), 'horario_sabado': request.form.get('horario_sabado'), 'horario_domingo': request.form.get('horario_domingo') }
            i = 0
            while f'servicio_nombre_{i}' in request.form:
                nombre = request.form[f'servicio_nombre_{i}']; precio = request.form[f'servicio_precio_{i}']; duracion = request.form[f'servicio_duracion_{i}']
                if nombre and precio and duracion: datos_negocio['servicios'].append({ 'nombre': nombre, 'precio': float(precio), 'duracion': int(duracion) })
                i += 1
            i = 0
            while f'empleado_nombre_{i}' in request.form:
                nombre = request.form[f'empleado_nombre_{i}']
                if nombre: datos_negocio['empleados'].append({'nombre': nombre})
                i += 1
            database.modificar_negocio_completo(negocio_id, datos_negocio)
            flash(f"Negocio '{datos_negocio['nombre']}' actualizado con éxito.", 'success')
        except Exception as e:
            print(f"Error al modificar negocio: {e}"); flash(f"Error al modificar negocio: {e}", 'error')
        return redirect(url_for('lista_negocios_ruta', password=password_ingresada))
    negocio_a_editar = database.obtener_negocio_por_id(negocio_id)
    return render_template('editar_negocio.html', negocio=negocio_a_editar, password=password_ingresada)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.FLASK_PORT, debug=True)