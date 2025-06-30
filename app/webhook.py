
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
import os
import logging
import requests
from openai import OpenAI
import mimetypes

# Activar logging
logging.basicConfig(level=logging.INFO)
router = APIRouter()

# Variables de entorno
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "clinico123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FIRMA_ACTIVA = os.getenv("FIRMA_ACTIVA", "true").lower() == "true"
NUMERO_DOCTOR = os.getenv("NUMERO_DOCTOR", "5217221623550")

# Cliente GPT
gpt = OpenAI(api_key=OPENAI_API_KEY)

# Cargar guía cetogénica y horarios
GUIA_KETO = """
Evita: azúcares, harinas, frutas ricas en carbohidratos, cereales.
Come libremente: carnes, pescados, huevos, aguacate, queso, vegetales verdes, aceite de oliva.
"""

HORARIOS = """
🕘 Consultas del Dr. Williams Barrios:
- Lunes a Viernes: 9:00 am – 1:00 pm y 4:00 pm – 7:00 pm
📍 Ubicación: Aesthetic Center, Metepec.
"""

# --- Filtro de mensajes triviales ---
def es_mensaje_irrelevante(texto: str) -> bool:
    texto = texto.strip().lower()
    return texto in ["hola", "ok", "gracias", "👍", "👌", "🙌", "🙋‍♂️"] or len(texto) < 4

# --- Verificación inicial (GET) ---
@router.get("/webhook")
async def verify_webhook(request: Request):
    if request.query_params.get("hub.mode") == "subscribe" and request.query_params.get("hub.verify_token") == VERIFY_TOKEN:
        return PlainTextResponse(request.query_params.get("hub.challenge"), status_code=200)
    return PlainTextResponse("Forbidden", status_code=403)

# --- Webhook principal (POST) ---
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
            texto = mensaje["text"]["body"]
            if es_mensaje_irrelevante(texto):
                return PlainTextResponse("EVENT_RECEIVED", status_code=200)
            respuesta = generar_respuesta_personalizada(texto, numero)

        elif tipo == "image":
            media_id = mensaje["image"]["id"]
            respuesta = analizar_imagen_clinica(media_id, numero)

        else:
            return PlainTextResponse("EVENT_RECEIVED", status_code=200)

        enviar_respuesta(numero, respuesta)
        return PlainTextResponse("EVENT_RECEIVED", status_code=200)

    except Exception as e:
        logging.error(f"❌ Error en webhook: {e}")
        return PlainTextResponse("ERROR", status_code=500)

# --- GPT: respuesta médica textual ---
def generar_respuesta_personalizada(texto_usuario: str, numero: str) -> str:
    es_doc = numero == NUMERO_DOCTOR
    prompt = f"""
Actúa como el Dr. Williams Barrios, médico en Aesthetic Center. 
Usa esta guía cetogénica:
{GUIA_KETO}

Horarios de consulta:
{HORARIOS}

El mensaje recibido es: "{texto_usuario}"

Tu respuesta debe:
- Ser empática, clara y profesional
- Sugerir visita presencial si aplica
- Nunca diagnosticar directamente
- Si es de administración, derivar con amabilidad
"""

    chat = gpt.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Eres el Dr. Williams Barrios. Responde profesionalmente, de forma responsable y humana."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.6
    )

    respuesta = chat.choices[0].message.content.strip()
    if FIRMA_ACTIVA and not es_doc:
        respuesta += "\n\n— Dr. Williams Barrios\nDirector Médico – Aesthetic Center"
    return respuesta

# --- GPT: análisis de imagen con visión ---
def analizar_imagen_clinica(media_id: str, numero: str) -> str:
    try:
        es_doc = numero == NUMERO_DOCTOR
        media_url = obtener_url_media(media_id)
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        image_data = requests.get(media_url, headers=headers).content

        vision = gpt.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {"role": "system", "content": (
                    "Eres el Dr. Williams Barrios, médico clínico con entrenamiento en medicina estética y nutrición. "
                    "Recibes imágenes clínicas por WhatsApp. Nunca diagnosticas con certeza sin valoración presencial. "
                    "Siempre recomiendas acudir a consulta. Tu lenguaje es cálido, empático y realista."
                )},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": (
                            "Analiza esta imagen como si fueras médico clínico. Describe lo que observas, "
                            "menciona posibles causas comunes, y concluye que debe valorarse presencialmente."
                        )},
                        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_data.encode('base64').decode()}}
                    ]
                }
            ],
            temperature=0.5
        )

        descripcion = vision.choices[0].message.content.strip()
        if FIRMA_ACTIVA and not es_doc:
            descripcion += "\n\n— Dr. Williams Barrios\nDirector Médico – Aesthetic Center"
        return descripcion

    except Exception as e:
        logging.error(f"❌ Error analizando imagen: {e}")
        return "Lo siento, no pude analizar la imagen. ¿Podrías volver a intentarlo o agendar una consulta presencial?"

# --- Descargar URL real de imagen desde WhatsApp ---
def obtener_url_media(media_id: str) -> str:
    url = f"https://graph.facebook.com/v18.0/{media_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    response = requests.get(url, headers=headers)
    return response.json()["url"]

# --- Enviar respuesta al usuario ---
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
