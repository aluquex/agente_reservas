# email_manager.py
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email import encoders
from datetime import datetime, timedelta
import uuid
import re
from jinja2 import Environment, FileSystemLoader, select_autoescape
import config

SMTP_SERVER = getattr(config, "MAIL_SMTP", "smtp.gmail.com")
SMTP_PORT = int(getattr(config, "MAIL_PORT", 587))
SMTP_USE_TLS = bool(getattr(config, "MAIL_USE_TLS", True))
MAIL_SENDER = getattr(config, "MAIL_SENDER", "no-reply@tu-dominio.com")
MAIL_PASSWORD = getattr(config, "MAIL_PASSWORD", "")

TZID = getattr(config, "ICAL_TZID", "Europe/Madrid")
DURACION_DEF_MIN = int(getattr(config, "CITA_DURACION_MIN", 30))

BRAND_LOGOS = {
    "dc barber": os.path.join("static", "logos", "dc_barber.png"),
    "dcb":       os.path.join("static", "logos", "dc_barber.png"),
    "dc_barber.jpeg": os.path.join("static", "logos", "dc_barber.jpeg"),
    "samuel":    os.path.join("static", "logos", "samuel_torrico.jpg"),
    "st":        os.path.join("static", "logos", "samuel_torrico.jpg"),
    "samue_torrico.jpg": os.path.join("static", "logos", "samue_torrico.jpg"),
}

TEMPLATES_DIR = os.path.join(os.getcwd(), "templates", "email")
_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"])
)

def _slugify(texto: str) -> str:
    t = (texto or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t

def _resolver_logo_path(negocio_nombre: str = None, negocio_slug: str = None) -> str | None:
    if negocio_slug:
        s = _slugify(negocio_slug)
        for k in (s, f"{s}.png", f"{s}.jpg", f"{s}.jpeg"):
            p = BRAND_LOGOS.get(k)
            if p and os.path.exists(p): return p
    if negocio_nombre:
        n = _slugify(negocio_nombre)
        for key, path in BRAND_LOGOS.items():
            if key in n and os.path.exists(path): return path

    base = os.path.join("static", "logos")
    candidatos = []
    if negocio_slug:
        s = _slugify(negocio_slug)
        candidatos += [os.path.join(base, f"{s}.{ext}") for ext in ("png", "jpg", "jpeg")]
    if negocio_nombre:
        n = _slugify(negocio_nombre).replace(" ", "_")
        candidatos += [os.path.join(base, f"{n}.{ext}") for ext in ("png", "jpg", "jpeg")]
    candidatos += [
        os.path.join(base, "dc_barber.jpeg"),
        os.path.join(base, "samue_torrico.jpg"),
    ]
    for c in candidatos:
        if os.path.exists(c): return c
    return None

def _cargar_logo_bytes(logo_path: str | None):
    if not logo_path: return None, None
    try:
        with open(logo_path, "rb") as f:
            data = f.read()
        ext = os.path.splitext(logo_path)[1].lstrip(".").lower() or "png"
        return data, ext
    except Exception:
        return None, None

def _formatear_fecha_hora_es(fecha_iso: str | datetime, hora_hhmm: str):
    if isinstance(fecha_iso, datetime):
        fecha = fecha_iso.date()
    else:
        fecha = datetime.fromisoformat(fecha_iso).date()
    h, m = map(int, hora_hhmm.split(":"))
    dt_inicio = datetime(fecha.year, fecha.month, fecha.day, h, m, 0)
    dt_fin = dt_inicio + timedelta(minutes=DURACION_DEF_MIN)
    dias = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
    meses = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
    fecha_legible = f"{dias[dt_inicio.weekday()]}, {dt_inicio.day} de {meses[dt_inicio.month-1]} de {dt_inicio.year}"
    return fecha_legible, f"{h:02d}:{m:02d}", dt_inicio, dt_fin

def _google_calendar_link(summary: str, dt_start: datetime, dt_end: datetime, details: str, location: str) -> str:
    def fmt(dt: datetime) -> str:
        return dt.strftime("%Y%m%dT%H%M%S")
    import urllib.parse
    params = {
        "action": "TEMPLATE",
        "text": summary,
        "dates": f"{fmt(dt_start)}/{fmt(dt_end)}",
        "details": details,
        "location": location or "",
    }
    return "https://calendar.google.com/calendar/render?" + urllib.parse.urlencode(params, safe=":/,")

def _build_ics(datos: dict, tipo: str, sequence: int | None = None) -> bytes:
    metodo = "REQUEST" if tipo in ("confirmacion", "modificacion", "recordatorio") else "CANCEL"
    if sequence is None:
        sequence = 0 if tipo == "confirmacion" else (1 if tipo == "modificacion" else (0 if tipo=="recordatorio" else 2))

    negocio_nombre = datos.get("negocio_nombre") or "Tu negocio"
    cliente_nombre = datos.get("nombre") or datos.get("nombre_cliente") or "Cliente"
    servicio = datos.get("servicio") or datos.get("servicio_despues") or datos.get("servicio_antes") or "Cita"
    fecha = datos.get("fecha")
    hora = datos.get("hora")
    direccion = datos.get("direccion") or ""
    email_negocio = datos.get("email_negocio")
    email_cliente = datos.get("email_cliente")

    _, _, dt_inicio, dt_fin = _formatear_fecha_hora_es(fecha, hora)
    uid = datos.get("ics_uid") or f"cita-{datos.get('negocio_id','x')}-{datos.get('cita_id',uuid.uuid4().hex)}@{(MAIL_SENDER.split('@')[-1])}"
    descripcion = f"{servicio} con {negocio_nombre}\\nCliente: {cliente_nombre}\\nTeléfono: {datos.get('telefono','')}"
    summary = f"{servicio} — {negocio_nombre}"

    def ics_dt(dt: datetime) -> str:
        return dt.strftime("%Y%m%dT%H%M%S")

    lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//SialWeb//Reserva Citas//ES",
        "VERSION:2.0",
        f"METHOD:{metodo}",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"SEQUENCE:{sequence}",
        f"DTSTAMP:{ics_dt(datetime.utcnow())}Z",
        f"DTSTART;TZID={TZID}:{ics_dt(dt_inicio)}",
        f"DTEND;TZID={TZID}:{ics_dt(dt_fin)}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{descripcion}",
        f"LOCATION:{direccion}",
    ]
    if email_negocio:
        lines.append(f"ORGANIZER;CN={negocio_nombre}:mailto:{email_negocio}")
    if email_cliente:
        lines.append(f"ATTENDEE;CN={cliente_nombre};ROLE=REQ-PARTICIPANT:mailto:{email_cliente}")
    lines += ["END:VEVENT","END:VCALENDAR"]
    return "\r\n".join(lines).encode("utf-8")

def _render_template(nombre_tpl: str, contexto: dict) -> str:
    template = _env.get_template(nombre_tpl)
    return template.render(**contexto)

def _send_mail(subject: str, to_list: list[str], html: str, text: str,
               ics_bytes: bytes | None = None,
               logo_bytes: bytes | None = None, logo_ext: str | None = None):
    if not to_list:
        return

    # mixed -> related -> (alternative + imagen) + adjuntos
    msg_root = MIMEMultipart("mixed")
    msg_root["From"] = MAIL_SENDER
    msg_root["To"] = ", ".join([t for t in to_list if t])
    msg_root["Subject"] = subject

    msg_related = MIMEMultipart("related")
    msg_alt = MIMEMultipart("alternative")
    msg_alt.attach(MIMEText(text or "", "plain", "utf-8"))
    msg_alt.attach(MIMEText(html or "", "html", "utf-8"))
    msg_related.attach(msg_alt)

    if logo_bytes:
        img = MIMEImage(logo_bytes, _subtype=(logo_ext or "png"))
        img.add_header("Content-ID", "<logo_cid>")
        img.add_header("Content-Disposition", "inline", filename=f"logo.{logo_ext or 'png'}")
        msg_related.attach(img)

    msg_root.attach(msg_related)

    if ics_bytes:
        ics = MIMEBase("text", "calendar", method="REQUEST", name="cita.ics")
        ics.set_payload(ics_bytes)
        encoders.encode_base64(ics)
        ics.add_header("Content-Disposition", "attachment", filename="cita.ics")
        ics.add_header("Content-Class", "urn:content-classes:calendarmessage")
        msg_root.attach(ics)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        if SMTP_USE_TLS:
            smtp.starttls()
        if MAIL_PASSWORD:
            smtp.login(MAIL_SENDER, MAIL_PASSWORD)
        smtp.sendmail(MAIL_SENDER, [t for t in to_list if t], msg_root.as_string())

def _build_contexto_comun(datos: dict, tipo: str):
    negocio_nombre = datos.get("negocio_nombre") or "Tu negocio"
    negocio_slug = datos.get("negocio_slug")
    cliente_nombre = datos.get("nombre") or datos.get("nombre_cliente") or "Cliente"
    fecha_legible, hora, dt_inicio, dt_fin = _formatear_fecha_hora_es(datos.get("fecha"), datos.get("hora"))
    servicio_actual = datos.get("servicio") or datos.get("servicio_despues") or datos.get("servicio_antes")
    empleado = datos.get("empleado_nombre") or "No asignado"
    direccion = datos.get("direccion") or ""
    telefono = datos.get("telefono") or ""
    logo_path = _resolver_logo_path(negocio_nombre, negocio_slug)
    logo_bytes, logo_ext = _cargar_logo_bytes(logo_path)
    logo_cid = "logo_cid" if logo_bytes else None

    summary = f"{servicio_actual or 'Cita'} — {negocio_nombre}"
    details = f"Cliente: {cliente_nombre} — Tel: {telefono}"
    gcal_url = _google_calendar_link(summary, dt_inicio, dt_fin, details, direccion)

    ctx = {
        "tipo": tipo,
        "negocio_nombre": negocio_nombre,
        "cliente_nombre": cliente_nombre,
        "servicio": servicio_actual,
        "empleado_nombre": empleado,
        "fecha_legible": fecha_legible,
        "hora": hora,
        "telefono": telefono,
        "direccion": direccion,
        "google_calendar_url": gcal_url,
        "servicio_antes": datos.get("servicio_antes"),
        "servicio_despues": datos.get("servicio_despues"),
        "logo_cid": logo_cid,
    }
    return ctx, logo_bytes, logo_ext

# ---------- Emails existentes ----------
def enviar_notificacion_cita(datos: dict):
    ctx, logo_bytes, logo_ext = _build_contexto_comun(datos, "confirmacion")
    html = _render_template("confirmacion.html", ctx)
    text = (f"Confirmación de cita — {ctx['negocio_nombre']}\n"
            f"Cliente: {ctx['cliente_nombre']}\n"
            f"Servicio: {ctx['servicio']}\n"
            f"Profesional: {ctx['empleado_nombre']}\n"
            f"Fecha: {ctx['fecha_legible']} a las {ctx['hora']}\n")
    ics = _build_ics(datos, "confirmacion", sequence=0)
    subject = f"✅ Confirmación de cita — {ctx['servicio']} ({ctx['fecha_legible']} {ctx['hora']})"
    to_list = [datos.get("email_negocio"), datos.get("email_cliente")]
    _send_mail(subject, to_list, html, text, ics_bytes=ics, logo_bytes=logo_bytes, logo_ext=logo_ext)

def enviar_notificacion_modificacion(datos: dict):
    ctx, logo_bytes, logo_ext = _build_contexto_comun(datos, "modificacion")
    html = _render_template("modificacion.html", ctx)
    text = (f"Tu cita ha sido modificada — {ctx['negocio_nombre']}\n"
            f"Nuevo servicio: {ctx['servicio']}\n"
            f"Profesional: {ctx['empleado_nombre']}\n"
            f"Nueva fecha: {ctx['fecha_legible']} a las {ctx['hora']}\n")
    ics = _build_ics(datos, "modificacion", sequence=1)
    subject = f"✏️ Cita actualizada — {ctx['servicio']} ({ctx['fecha_legible']} {ctx['hora']})"
    to_list = [datos.get("email_negocio"), datos.get("email_cliente")]
    _send_mail(subject, to_list, html, text, ics_bytes=ics, logo_bytes=logo_bytes, logo_ext=logo_ext)

def enviar_notificacion_cancelacion(datos: dict):
    ctx, logo_bytes, logo_ext = _build_contexto_comun(datos, "cancelacion")
    html = _render_template("cancelacion.html", ctx)
    text = (f"Tu cita ha sido cancelada — {ctx['negocio_nombre']}\n"
            f"Servicio: {ctx['servicio']}\n"
            f"Fecha cancelada: {ctx['fecha_legible']} {ctx['hora']}\n")
    ics = _build_ics(datos, "cancelacion", sequence=2)
    subject = f"❌ Cita cancelada — {ctx['servicio']} ({ctx['fecha_legible']} {ctx['hora']})"
    to_list = [datos.get("email_negocio"), datos.get("email_cliente")]
    _send_mail(subject, to_list, html, text, ics_bytes=ics, logo_bytes=logo_bytes, logo_ext=logo_ext)

# ---------- NUEVO: Recordatorio 2h ----------
def enviar_recordatorio_cita(datos: dict):
    """
    Recordatorio 2h antes (email + .ICS con METHOD:REQUEST).
    """
    ctx, logo_bytes, logo_ext = _build_contexto_comun(datos, "recordatorio")
    html = _render_template("recordatorio.html", ctx)
    text = (f"Recordatorio de cita — {ctx['negocio_nombre']}\n"
            f"Cliente: {ctx['cliente_nombre']}\n"
            f"Servicio: {ctx['servicio']}\n"
            f"Profesional: {ctx['empleado_nombre']}\n"
            f"Hoy a las {ctx['hora']}\n")
    ics = _build_ics(datos, "recordatorio", sequence=0)
    subject = f"⏰ Recordatorio: {ctx['servicio']} hoy a las {ctx['hora']}"
    to_list = [datos.get("email_cliente")]  # foco en el cliente; añade negocio si quieres copia
    _send_mail(subject, to_list, html, text, ics_bytes=ics, logo_bytes=logo_bytes, logo_ext=logo_ext)
