# app.py
from flask import Flask, request, jsonify, session
from flask_cors import CORS
import config
import handlers

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

CORS(
    app,
    resources={r"/mensaje": {"origins": list(config.CORS_ALLOWED_ORIGINS)}},
    supports_credentials=True
)

GESTION_KEYWORDS = ['consultar', 'modificar', 'cambiar', 'cancelar', 'anular', 'ver mi cita']

# El director de orquesta final y completo
ESTADO_HANDLERS = {
    'pidiendo_nombre': handlers.handle_peticion_nombre,
    'pidiendo_telefono': handlers.handle_peticion_telefono,
    'pidiendo_servicio': handlers.handle_peticion_servicio,
    'pidiendo_hora': handlers.handle_peticion_hora,
    'confirmar_cita': handlers.handle_confirmar_cita,
    'gestion_pide_telefono': handlers.handle_gestion_pide_telefono,
    'gestion_confirmar_cancelacion': handlers.handle_gestion_confirmar_cancelacion,
    'gestion_pide_campo_a_modificar': handlers.handle_gestion_pide_campo_a_modificar,
    'modificar_confirmar_hora': handlers.handle_modificar_confirmar_hora,
}

@app.route("/mensaje", methods=["POST"])
def mensaje():
    texto_usuario = request.json.get("mensaje", "").strip()
    estado_actual = session.get('estado')
    
    # La lógica de enrutamiento simplificada y robusta
    if any(keyword in texto_usuario.lower() for keyword in GESTION_KEYWORDS) and estado_actual not in ['gestion_pide_telefono', 'gestion_confirmar_cancelacion', 'gestion_pide_campo_a_modificar']:
        respuesta_dict = handlers.handle_inicio_gestion(texto_usuario)
    else:
        handler_func = ESTADO_HANDLERS.get(estado_actual)
        if handler_func:
            respuesta_dict = handler_func(texto_usuario)
        else:
            respuesta_dict = handlers.handle_bienvenida(texto_usuario)
        
    return jsonify(respuesta_dict)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.FLASK_PORT, debug=True)