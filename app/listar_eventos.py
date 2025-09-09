
import os
import json
import logging
from datetime import datetime, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build

# Variables de entorno
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")

def obtener_servicio_calendar():
    try:
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/calendar"]
        )
        return build("calendar", "v3", credentials=creds)
    except Exception as e:
        logging.error(f"❌ Error al conectar con Google Calendar: {e}")
        return None

def listar_eventos_hoy():
    try:
        service = obtener_servicio_calendar()
        if not service:
            return "No se pudo conectar a Google Calendar."

        zona = "America/Mexico_City"
        ahora = datetime.now().astimezone()
        inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        fin = ahora.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

        eventos = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=inicio,
            timeMax=fin,
            singleEvents=True,
            orderBy="startTime"
        ).execute().get("items", [])

        if not eventos:
            return "Hoy no hay citas agendadas."

        texto = "📅 *Citas para hoy:*\n"
        for e in eventos:
            resumen = e.get("summary", "Sin título")
            hora = e["start"]["dateTime"][11:16]
            texto += f"• {hora} — {resumen}\n"
        return texto.strip()
    except Exception as e:
        logging.error(f"❌ Error al listar eventos: {e}")
        return "Error al obtener las citas de hoy."
