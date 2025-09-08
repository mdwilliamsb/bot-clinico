import os
import json
import pytz
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Cargar credenciales desde variable de entorno segura
json_str = os.getenv("GOOGLE_CREDENTIALS_JSON")
info = json.loads(json_str)
credentials = service_account.Credentials.from_service_account_info(
    info,
    scopes=["https://www.googleapis.com/auth/calendar"]
)

# Conectarse a la API de Google Calendar
service = build("calendar", "v3", credentials=credentials)
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")  # Puedes fijarlo como variable también

# --- Crear evento en Google Calendar ---
def agendar_evento(nombre: str, fecha: str, motivo: str = "Consulta médica"):
    """
    Agenda un evento en el calendario.
    - nombre: nombre del paciente
    - fecha: formato 'YYYY-MM-DD HH:MM' (hora 24h)
    - motivo: motivo de consulta
    """

    zona_horaria = pytz.timezone("America/Mexico_City")
    inicio = zona_horaria.localize(datetime.strptime(fecha, "%Y-%m-%d %H:%M"))
    fin = inicio + timedelta(minutes=30)

    evento = {
        "summary": f"Cita con {nombre}",
        "description": motivo,
        "start": {"dateTime": inicio.isoformat(), "timeZone": "America/Mexico_City"},
        "end": {"dateTime": fin.isoformat(), "timeZone": "America/Mexico_City"},
    }

    creado = service.events().insert(calendarId=CALENDAR_ID, body=evento).execute()
    return creado.get("htmlLink", "Cita creada.")
