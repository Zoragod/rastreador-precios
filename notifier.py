import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Tuple, Optional
from dotenv import load_dotenv

load_dotenv()

# Símbolo de moneda predeterminado: Sol Peruano
SIMBOLO_MONEDA = "S/."

def obtener_config_smtp():
    """Obtiene la configuración SMTP desde las variables de entorno."""
    return {
        "servidor": os.getenv("SMTP_SERVER", "smtp.gmail.com").strip(),
        "puerto": int(os.getenv("SMTP_PORT", 587)),
        "usuario": os.getenv("SMTP_USER", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip(),
        "destinatario": os.getenv("EMAIL_NOTIFICACION", "").strip() or os.getenv("SMTP_USER", "").strip(),
    }

def esta_configurado() -> bool:
    """Verifica si las credenciales de correo están configuradas."""
    cfg = obtener_config_smtp()
    return bool(cfg["usuario"] and cfg["password"] and cfg["destinatario"])

def enviar_alerta_oferta(
    nombre_producto: str,
    tienda: str,
    url_producto: str,
    precio_actual: float,
    precio_objetivo: float,
    precio_minimo: Optional[float] = None,
    moneda: str = "S/."
) -> Tuple[bool, str]:
    """
    Envía un correo con diseño HTML cuando un producto alcanza o mejora el precio objetivo en Soles (S/.).
    """
    cfg = obtener_config_smtp()
    
    if not esta_configurado():
        return False, "SMTP no configurado en las variables de entorno de Render (faltan SMTP_USER o SMTP_PASSWORD)."

    ahorro = precio_objetivo - precio_actual
    ahorro_txt = f"¡Ahorras {moneda} {ahorro:.2f} respecto a tu meta!" if ahorro > 0 else "¡Alcanzó exactamente tu precio objetivo!"
    
    asunto = f"🎯 ¡Oferta Detectada! {nombre_producto} a {moneda} {precio_actual:.2f}"

    cuerpo_texto = f"""
¡Gran noticia! El producto que sigues acaba de entrar en oferta:

Producto: {nombre_producto}
Tienda: {tienda}
Precio Actual: {moneda} {precio_actual:.2f}
Tu Precio Objetivo: {moneda} {precio_objetivo:.2f}
{ahorro_txt}

Puedes verlo y comprarlo en el siguiente enlace:
{url_producto}

Enviado automáticamente por tu Rastreador de Precios.
"""

    cuerpo_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f4f6f8;
            margin: 0;
            padding: 20px;
        }}
        .card {{
            background: #ffffff;
            border-radius: 12px;
            max-width: 550px;
            margin: 0 auto;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            border: 1px solid #e1e4e8;
        }}
        .header {{
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: #ffffff;
            padding: 24px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 22px;
        }}
        .content {{
            padding: 24px;
            color: #333333;
        }}
        .price-box {{
            background-color: #ecfdf5;
            border: 2px dashed #10b981;
            border-radius: 8px;
            padding: 16px;
            text-align: center;
            margin: 20px 0;
        }}
        .price-main {{
            font-size: 32px;
            font-weight: bold;
            color: #065f46;
        }}
        .badge {{
            display: inline-block;
            background: #d1fae5;
            color: #047857;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            margin-top: 6px;
        }}
        .details {{
            margin: 16px 0;
            font-size: 14px;
            line-height: 1.6;
        }}
        .btn {{
            display: block;
            text-align: center;
            background-color: #2563eb;
            color: #ffffff !important;
            text-decoration: none;
            padding: 14px 20px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 16px;
            margin: 24px 0 10px 0;
        }}
        .footer {{
            text-align: center;
            font-size: 12px;
            color: #888888;
            padding: 16px;
            background: #fafafa;
            border-top: 1px solid #eeeeee;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>🎯 ¡Oferta Alcanzada!</h1>
        </div>
        <div class="content">
            <h2 style="margin-top: 0; color: #111827;">{nombre_producto}</h2>
            <p style="color: #6b7280; margin: 0 0 15px 0;">Tienda: <strong>{tienda}</strong></p>
            
            <div class="price-box">
                <div style="font-size: 13px; color: #047857; text-transform: uppercase; font-weight: 600;">Precio Actual</div>
                <div class="price-main">{moneda} {precio_actual:.2f}</div>
                <div class="badge">{ahorro_txt}</div>
            </div>

            <div class="details">
                <p>🎯 <strong>Tu precio objetivo:</strong> {moneda} {precio_objetivo:.2f}</p>
                {"<p>📉 <strong>Mínimo histórico:</strong> " + moneda + f" {precio_minimo:.2f}" + "</p>" if precio_minimo else ""}
            </div>

            <a href="{url_producto}" target="_blank" class="btn">👉 Ver Producto en la Tienda</a>
        </div>
        <div class="footer">
            Generado automáticamente por tu Rastreador de Precios y Ofertas.
        </div>
    </div>
</body>
</html>
"""

    return _enviar_email(
        remitente=cfg["usuario"],
        password=cfg["password"],
        servidor=cfg["servidor"],
        puerto=cfg["puerto"],
        destinatario=cfg["destinatario"],
        asunto=asunto,
        cuerpo_texto=cuerpo_texto,
        cuerpo_html=cuerpo_html
    )

def enviar_correo_prueba(destinatario: Optional[str] = None) -> Tuple[bool, str]:
    """Envía un correo de prueba para validar la configuración SMTP."""
    cfg = obtener_config_smtp()
    dest = destinatario or cfg["destinatario"]

    if not esta_configurado():
        return False, "Faltan credenciales SMTP. Revisa la sección Environment Variables en Render."

    asunto = "✅ Prueba de Notificaciones - Rastreador de Precios"
    cuerpo_texto = "¡Hola! La conexión con tu servidor de correo funciona perfectamente desde Render."
    cuerpo_html = """
    <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
        <h2 style="color: #10b981;">✅ Conexión SMTP Exitosa</h2>
        <p>¡Hola! Las notificaciones automáticas de tu <strong>Rastreador de Precios y Ofertas</strong> están funcionando perfectamente en Render.</p>
        <p>A partir de ahora recibirás un correo automático cada vez que un producto alcance o supere tu precio objetivo en <strong>Soles Peruanos (S/.)</strong>.</p>
    </div>
    """

    return _enviar_email(
        remitente=cfg["usuario"],
        password=cfg["password"],
        servidor=cfg["servidor"],
        puerto=cfg["puerto"],
        destinatario=dest,
        asunto=asunto,
        cuerpo_texto=cuerpo_texto,
        cuerpo_html=cuerpo_html
    )

def _enviar_email(
    remitente: str,
    password: str,
    servidor: str,
    puerto: int,
    destinatario: str,
    asunto: str,
    cuerpo_texto: str,
    cuerpo_html: str
) -> Tuple[bool, str]:
    """
    Gestiona la conexión y envío vía SMTP con soporte dual para puertos 587 (STARTTLS) y 465 (SSL).
    Si un puerto falla o da timeout en servidores cloud (Render), intenta automáticamente con el otro.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = f"Rastreador de Precios <{remitente}>"
    msg["To"] = destinatario

    msg.attach(MIMEText(cuerpo_texto, "plain", "utf-8"))
    msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    # Intentar primero con el puerto configurado
    puertos_a_intentar = [puerto]
    puerto_alterno = 465 if puerto == 587 else 587
    puertos_a_intentar.append(puerto_alterno)

    ultimo_error = None

    for p in puertos_a_intentar:
        try:
            if p == 465:
                with smtplib.SMTP_SSL(servidor, p, timeout=12) as server:
                    server.login(remitente, password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(servidor, p, timeout=12) as server:
                    server.starttls()
                    server.login(remitente, password)
                    server.send_message(msg)

            return True, f"Correo enviado exitosamente a {destinatario}."
        except smtplib.SMTPAuthenticationError:
            return False, "Error de autenticación SMTP: Verifica que la Contraseña de Aplicación de 16 letras sea correcta."
        except Exception as e:
            ultimo_error = e
            continue

    return False, f"Error al enviar correo (se intentaron puertos 587 y 465): {ultimo_error}"
