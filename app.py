# app.py
from flask import Flask, request, jsonify, session
from flask_cors import CORS
import config
import handlers
import utils # Importamos utils para poder normalizar el texto

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

CORS( app, resources={r"/mensaje": {"origins": list(config.CORS_ALLOWED_ORIGINS)}}, supports_credentials=True )

# --- LISTA DE PALABRAS CLAVE DE REINICIO AMPLIADA Y MEJORADA ---
REINICIO_KEYWORDS = [
    'empezar', 'iniciar', 'volver', 'atras', 
    'reinicio', 'inicio', 'menu', 'reset'
]

ESTADO_HANDLERS = {
    'esperando_eleccion_inicial': handlers.handle_eleccion_inicial,
    'pidiendo_nombre': handlers.handle_peticion_nombre,
    'pidiendo_telefono': handlers.handle_peticion_telefono,
    'pidiendo_servicio': handlers.handle_peticion_servicio,
    'pidiendo_hora': handlers.handle_peticion_hora,
    'confirmar_cita': handlers.handle_confirmar_cita,
    'gestion_pide_telefono': handlers.handle_gestion_pide_telefono,
    'gestion_esperando_accion': handlers.handle_gestion_esperando_accion,
    'gestion_confirmar_cancelacion': handlers.handle_gestion_confirmar_cancelacion,
    'gestion_pide_campo_a_modificar': handlers.handle_gestion_pide_campo_a_modificar,
    'modificar_confirmar_hora': handlers.handle_modificar_confirmar_hora,
}

@app.route("/mensaje", methods=["POST"])
def mensaje():
    texto_usuario = request.json.get("mensaje", "").strip()
    # Normalizamos el texto del usuario para que no importen acentos ni mayúsculas
    texto_normalizado = utils.normalizar_texto(texto_usuario)
    estado_actual = session.get('estado')
    
    # REGLA 1: La palabra de seguridad para reiniciar tiene prioridad sobre todo.
    if any(keyword in texto_normalizado for keyword in REINICIO_KEYWORDS):
        respuesta_dict = handlers.handle_bienvenida(texto_usuario)
        return jsonify(respuesta_dict)

    # REGLA 2: Buscamos un handler para el estado actual.
    handler_func = ESTADO_HANDLERS.get(estado_actual)
    
    if handler_func:
        respuesta_dict = handler_func(texto_usuario)
    else:
        respuesta_dict = handlers.handle_bienvenida(texto_usuario)
    
    # REGLA 3 (Mensaje por defecto): Si el handler no supo qué responder.
    if not respuesta_dict.get("respuesta"):
         respuesta_dict = {
             "respuesta": "Lo siento, no te he entendido. ¿Quieres 'Agendar Cita' o 'Gestionar Cita'?"
         }
        
    return jsonify(respuesta_dict)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.FLASK_PORT, debug=True)