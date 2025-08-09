# app.py
from flask import Flask, request, jsonify, session, send_from_directory
import handlers
import utils

app = Flask(__name__)
app.secret_key = 'clave-secreta-para-probar-12345'
app.config['PERMANENT_SESSION_LIFETIME'] = utils.timedelta(minutes=30)

ESTADO_HANDLERS = {
    'pidiendo_nombre': handlers.handle_peticion_nombre,
    'pidiendo_telefono': handlers.handle_peticion_telefono,
    'pidiendo_servicio': handlers.handle_peticion_servicio,
    'pidiendo_fecha': handlers.handle_peticion_fecha,
    'pidiendo_hora': handlers.handle_peticion_hora,
    'gestion_pide_telefono': handlers.handle_gestion_pide_telefono,
    'gestion_confirmar_cancelacion': handlers.handle_gestion_confirmar_cancelacion,
    # Estados para el nuevo flujo de modificación
    'modificar_pide_campo': handlers.handle_modificar_pide_campo,
}

@app.route("/mensaje", methods=["POST"])
def mensaje():
    data = request.get_json()
    texto_usuario = data.get("mensaje", "").strip()
    
    estado_actual = session.get('estado')
    texto_norm = utils.normalizar_texto(texto_usuario)
    
    if any(keyword in texto_norm for keyword in ["consultar", "modificar", "cancelar"]):
        return handlers.handle_inicio_gestion(texto_usuario)

    if estado_actual:
        handler_func = ESTADO_HANDLERS.get(estado_actual)
        if handler_func:
            return handler_func(texto_usuario)
        else:
            session.clear()
            return handlers.handle_fallback(texto_usuario)
    
    return handlers.handle_bienvenida(texto_usuario)

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

