# whatsapp_manager.py
import os
import re
from datetime import datetime
import config

# Twilio
try:
    from twilio.rest import Client
except Exception:
    Client = None

TW_SID  = getattr(config, "TWILIO_ACCOUNT_SID", os.getenv("TWILIO_ACCOUNT_SID", ""))
TW_TOK  = getattr(config, "TWILIO_AUTH_TOKEN",  os.getenv("TWILIO_AUTH_TOKEN", ""))
# Sandbox / número verificado de WhatsApp Business
TW_FROM = getattr(config, "TWILIO_WHATSAPP_FROM", os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"))

DEFAULT_CC = getattr(config, "DEFAULT_COUNTRY_CODE", os.getenv("DEFAULT_COUNTRY_CODE", "+34"))

def _to_e164(telefono: str) -> str | None:
    if not telefono:
        return None
    tel = re.sub(r"\D+", "", telefono)  # quitar no dígitos
    if telefono.strip().startswith("+"):
        return "+" + tel
    # Si no empieza por +, anteponer país (España por defecto)
    return DEFAULT_CC + tel

def enviar_recordatorio_whatsapp(datos: dict):
    """
    Envía un mensaje de WhatsApp 2h antes de la cita.
    Requiere credenciales de Twilio y que el destinatario esté autorizado (sandbox/prod).
    """
    if not Client:
        print("[WhatsApp] Twilio SDK no disponible. Instala 'twilio' en requirements.txt")
        return

    to = _to_e164(datos.get("telefono"))
    if not to:
        return

    cliente = Client(TW_SID, TW_TOK)

    negocio = datos.get("negocio_nombre") or "Tu negocio"
    servicio = datos.get("servicio") or "Cita"
    hora     = datos.get("hora")
    fecha    = datos.get("fecha")
    empleado = datos.get("empleado_nombre") or "nuestro equipo"
    direccion = datos.get("direccion") or ""

    body = (
        f"⏰ Recordatorio de cita\n"
        f"{negocio}\n"
        f"Servicio: {servicio}\n"
        f"Profesional: {empleado}\n"
        f"Hoy {fecha} a las {hora}\n"
        f"{'Dirección: ' + direccion if direccion else ''}\n\n"
        f"Si no puedes asistir, responde a este mensaje para reprogramar. ¡Gracias!"
    )

    try:
        cliente.messages.create(
            from_=TW_FROM,
            to=f"whatsapp:{to}",
            body=body
        )
        print(f"[WhatsApp] Recordatorio enviado a {to}")
    except Exception as e:
        print(f"[WhatsApp] Error enviando a {to}: {e}")
