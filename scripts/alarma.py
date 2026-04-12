import smtplib
from email.message import EmailMessage
import constants as c


def enviar_alarma_icloud(hora):
    # --- CONFIGURACIÓN ---
    tu_correo_icloud = "nesbe717@icloud.com"  # Tu dirección real
    password_aplicacion = "rnqf-pvpa-zutr-hnrz"  # La clave de 16 letras de Apple

    # Creamos el mensaje
    msg = EmailMessage()
    msg.set_content(f"Activando alarma para las {hora}")
    msg['Subject'] = f"ALARM:{hora}"  # El "trigger" para el iPhone
    msg['From'] = c.ICLOUD_EMAIL
    msg['To'] = c.ICLOUD_EMAIL  # Te lo envías a ti mismo

    try:
        # Configuración del servidor de Apple
        # iCloud usa el puerto 587 con STARTTLS
        server = smtplib.SMTP('smtp.mail.me.com', 587)
        server.starttls()  # Cifrado de seguridad obligatorio para Apple
        server.login(c.ICLOUD_EMAIL, c.ICLOUD_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"🚀 Email enviado a iCloud. Alarma programada: {hora}")
    except Exception as e:
        print(f"❌ Error al enviar: {e}")