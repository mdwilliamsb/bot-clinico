
import os
import json
import logging
from datetime import datetime, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.utils import interpretar_fecha_hora
from app.webhook import enviar_respuesta

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

def crear_evento_calendar(nombre: str, telefono: str, nota: str) -> str:
    try:
        service = obtener_servicio_calendar()
        if not service:
            return "No se pudo conectar a Google Calendar."

        fecha_hora = interpretar_fecha_hora(nota)
        inicio = fecha_hora.isoformat()
        fin = (fecha_hora + timedelta(minutes=30)).isoformat()

        # Verificar duplicados
        eventos = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=fecha_hora.isoformat(),
            timeMax=(fecha_hora + timedelta(minutes=30)).isoformat(),
            singleEvents=True,
            orderBy="startTime"
        ).execute().get("items", [])

        for e in eventos:
            if nombre.lower() in e.get("summary", "").lower():
                logging.info("Evento duplicado detectado. No se agenda.")
                enviar_respuesta(telefono, f"Ya tienes una cita registrada para ese horario.")
                return "Evento ya existe"

        evento = {
            "summary": f"Cita con {nombre}",
            "description": nota,
            "start": {"dateTime": inicio, "timeZone": "America/Mexico_City"},
            "end": {"dateTime": fin, "timeZone": "America/Mexico_City"},
        }

        creado = service.events().insert(calendarId=CALENDAR_ID, body=evento).execute()

        # Confirmar cita por WhatsApp
        mensaje = (
            f"✅ Tu cita ha sido agendada para el {fecha_hora.strftime('%A %d de %B a las %H:%M')}.\n"
    "📍 Ubicación: Aesthetic Center, Metepec.\n"
    "Gracias por tu confianza.\n"
    "— Dr. Williams Barrios"
        )
        enviar_respuesta(telefono, mensaje)
        return "Evento creado y confirmado"
    except Exception as e:
        logging.error(f"❌ Error creando evento: {e}")
        enviar_respuesta(telefono, "Hubo un problema al agendar tu cita. Intenta más tarde.")
        return "Error"
