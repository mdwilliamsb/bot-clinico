
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
import os
import logging
import requests
import base64
from openai import OpenAI

from app.memoria import (
    inicializar_db,
    guardar_mensaje,
    recuperar_historial,
    recuperar_nombre,
    actualizar_nombre,
    detectar_intencion
)
from app.calendar import crear_evento_calendar
from app.listar_eventos import listar_eventos_hoy
from app.utils import interpretar_fecha_hora

# 🧠 Verificación automática de base de datos
if not os.path.exists("data/memoria.db"):
    inicializar_db()

logging.basicConfig(level=logging.INFO)
router = APIRouter()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "clinico123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NUMERO_DOCTOR = os.getenv("NUMERO_DOCTOR", "5217221623550")
FIRMA_ACTIVA = os.getenv("FIRMA_ACTIVA", "true").lower() == "true"

gpt = OpenAI(api_key=OPENAI_API_KEY)

GUIA_KETO = "Evita azúcares, harinas, frutas ricas en carbohidratos. Prioriza proteína, grasa buena y vegetales verdes."
HORARIOS = "Consultas: Lunes a Viernes de 9:00–13:00 y 16:00–19:00 en Aesthetic Center, Metepec."

def es_mensaje_irrelevante(texto: str) -> bool:
    texto = texto.strip().lower()
    return texto in ["hola", "ok", "gracias", "👍", "👌", "🙌"] or len(texto) < 4

@router.get("/webhook")
async def verify_webhook(request: Request):
    if request.query_params.get("hub.mode") == "subscribe" and request.query_params.get("hub.verify_token") == VERIFY_TOKEN:
        return PlainTextResponse(content=request.query_params.get("hub.challenge"), status_code=200)
    return PlainTextResponse("Forbidden", status_code=403)

@router.post("/webhook")
async def recibir_mensaje(request: Request):
    try:
        data = await request.json()
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return PlainTextResponse("EVENT_RECEIVED", status_code=200)

        mensaje = value["messages"][0]
        numero = mensaje.get("from")
        tipo = mensaje.get("type")

        if tipo == "text":
            texto = mensaje["text"]["body"].strip()

            if es_mensaje_irrelevante(texto):
                return PlainTextResponse("EVENT_RECEIVED", status_code=200)

            if texto.lower() in ["/citas", "/resumen"]:
                resumen = listar_eventos_hoy()
                enviar_respuesta(numero, resumen)
                return PlainTextResponse("EVENT_RECEIVED", status_code=200)

            if texto.lower() == "/recordar":
                historial = recuperar_historial(numero)
                respuesta = f"Este es tu historial reciente:\n{historial or 'No tengo registro previo contigo.'}"
                enviar_respuesta(numero, respuesta)
                return PlainTextResponse("EVENT_RECEIVED", status_code=200)

            guardar_mensaje(numero, texto)
            actualizar_nombre(numero, texto)
            respuesta = generar_respuesta_personalizada(numero, texto)

            # Intención: agendar
            if detectar_intencion(texto).lower() in ["agendar", "cita", "consulta"]:
                crear_evento_calendar(recuperar_nombre(numero), numero, texto)

        elif tipo == "image":
            media_id = mensaje["image"]["id"]
            respuesta = analizar_imagen(numero, media_id)

        else:
            return PlainTextResponse("EVENT_RECEIVED", status_code=200)

        enviar_respuesta(numero, respuesta)
        return PlainTextResponse("EVENT_RECEIVED", status_code=200)

    except Exception as e:
        logging.error(f"❌ Error en webhook: {e}")
        return PlainTextResponse("Error interno", status_code=500)

def generar_respuesta_personalizada(numero: str, texto_usuario: str) -> str:
    es_doc = numero == NUMERO_DOCTOR
    nombre = recuperar_nombre(numero) or "paciente"
    historial = recuperar_historial(numero)
    intencion = detectar_intencion(texto_usuario)

    prompt = f"""Soy el Dr. Williams Barrios, médico pediatra con enfoque en nutrición, dieta cetogénica y salud integral.
Respondo personalmente los mensajes por WhatsApp con respeto y orientación profesional.

Paciente: {nombre}
Intención del mensaje: {intencion}
Historial reciente:
{historial}

Mensaje actual: "{texto_usuario}"

Tu respuesta debe ser:
- Cálida y profesional
- Basada en el historial
- Sin diagnosticar directamente
- Sugerir consulta si aplica
"""

    chat = gpt.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Actúas como el Dr. Williams Barrios, humano, médico experto y cercano."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.55
    )

    respuesta = chat.choices[0].message.content.strip()
    if FIRMA_ACTIVA and not es_doc:
        respuesta += "\n\n— Dr. Williams Barrios\nPediatra y Nutriólogo Clínico\nDirector Médico – Aesthetic Center"
    return respuesta

def analizar_imagen(numero: str, media_id: str) -> str:
    try:
        es_doc = numero == NUMERO_DOCTOR
        media_url = obtener_url_media(media_id)
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        image_data = requests.get(media_url, headers=headers).content
        image_base64 = base64.b64encode(image_data).decode("utf-8")

        vision = gpt.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {"role": "system", "content": (
                    "Eres el Dr. Williams Barrios, médico pediatra y clínico. Analizas imágenes médicas con responsabilidad. "
                    "Describes observaciones, causas probables y recomiendas valoración en consulta presencial."
                )},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analiza clínicamente la imagen. Sugiere pero no diagnostiques. Recomienda consulta médica."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                }
            ],
            temperature=0.5
        )
        respuesta = vision.choices[0].message.content.strip()
        if FIRMA_ACTIVA and not es_doc:
            respuesta += "\n\n— Dr. Williams Barrios\nPediatra y Nutriólogo Clínico\nDirector Médico – Aesthetic Center"
        return respuesta

    except Exception as e:
        logging.error(f"❌ Error analizando imagen: {e}")
        return "No pude analizar la imagen. ¿Podrías enviarla de nuevo o acudir a consulta presencial?"

def obtener_url_media(media_id: str) -> str:
    url = f"https://graph.facebook.com/v18.0/{media_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    response = requests.get(url, headers=headers)
    return response.json()["url"]

def enviar_respuesta(numero: str, mensaje: str):
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }
    res = requests.post(url, json=payload, headers=headers)
    logging.info(f"📤 Respuesta enviada a {numero}: {res.status_code}")
