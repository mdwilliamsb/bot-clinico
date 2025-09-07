from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
import os
import logging
import requests
import json
from openai import OpenAI
import base64

# Configuración
logging.basicConfig(level=logging.INFO)
router = APIRouter()

# Variables de entorno
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "clinico123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NUMERO_DOCTOR = os.getenv("NUMERO_DOCTOR", "5217221623550")
FIRMA_ACTIVA = os.getenv("FIRMA_ACTIVA", "true").lower() == "true"

# Cliente GPT
gpt = OpenAI(api_key=OPENAI_API_KEY)

# Contexto personalizado
GUIA_KETO = "Evita azúcares, harinas, frutas ricas en carbohidratos. Prioriza proteína, grasa buena y vegetales verdes."
HORARIOS = "Consultas: Lunes a Viernes de 9:00–13:00 y 16:00–19:00 en Aesthetic Center, Metepec."

# Filtro de saludos triviales
def es_mensaje_irrelevante(texto: str) -> bool:
    texto = texto.strip().lower()
    return texto in ["hola", "ok", "gracias", "👍", "👌", "🙌"] or len(texto) < 4

# GET: Verificación del webhook
@router.get("/webhook")
async def verify_webhook(request: Request):
    if request.query_params.get("hub.mode") == "subscribe" and request.query_params.get("hub.verify_token") == VERIFY_TOKEN:
        return PlainTextResponse(content=request.query_params.get("hub.challenge"), status_code=200)
    return PlainTextResponse("Forbidden", status_code=403)

# POST: Recepción de mensajes
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
            respuesta = generar_respuesta_estilo_williams(texto, numero)

        elif tipo == "image":
            media_id = mensaje["image"]["id"]
            respuesta = analizar_imagen_estilo_williams(media_id, numero)

        else:
            return PlainTextResponse("EVENT_RECEIVED", status_code=200)

        enviar_respuesta(numero, respuesta)
        return PlainTextResponse("EVENT_RECEIVED", status_code=200)

    except Exception as e:
        logging.error(f"❌ Error en webhook: {e}")
        return PlainTextResponse("Error interno", status_code=500)

# GPT: Estilo médico profesional personalizado
def generar_respuesta_estilo_williams(texto_usuario: str, numero: str) -> str:
    es_doc = numero == NUMERO_DOCTOR
    prompt = f"""
Soy el Dr. Williams Barrios, médico pediatra con enfoque en nutrición, dieta cetogénica y salud integral.
Respondo personalmente los mensajes de mis pacientes por WhatsApp con claridad, respeto y orientación clínica profesional.
También atiendo temas comunes como alergias, infecciones, problemas digestivos y control de peso.

Horarios: {HORARIOS}
Guía nutricional base: {GUIA_KETO}

Mensaje del paciente: "{texto_usuario}"

Mi respuesta debe ser:
- Clara y humana
- Responsable y útil
- Sin diagnosticar de forma directa
- Siempre recordando la importancia de una consulta presencial
"""

    chat = gpt.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Actúas como el Dr. Williams Barrios, médico pediatra con especialidad en nutrición y estética, respondiendo personalmente."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.55
    )

    respuesta = chat.choices[0].message.content.strip()
    if FIRMA_ACTIVA and not es_doc:
        respuesta += "

— Dr. Williams Barrios
Pediatra y Nutriólogo Clínico
Director Médico – Aesthetic Center"
    return respuesta

# GPT-4 Vision: Análisis clínico de imagen
def analizar_imagen_estilo_williams(media_id: str, numero: str) -> str:
    try:
        es_doc = numero == NUMERO_DOCTOR
        media_url = obtener_url_media(media_id)
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        image_data = requests.get(media_url, headers=headers).content
        image_base64 = base64.b64encode(image_data).decode("utf-8")

        chat = gpt.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {"role": "system", "content": (
                    "Eres el Dr. Williams Barrios, médico pediatra y clínico. Analizas imágenes médicas por WhatsApp con profesionalismo. "
                    "Describes lo que observas, das posibles causas probables, y siempre recomiendas valoración en consulta presencial."
                )},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analiza la imagen médica del paciente de forma responsable. Menciona qué podría ser, pero sugiere acudir a consulta para confirmar."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                }
            ],
            temperature=0.5
        )

        descripcion = chat.choices[0].message.content.strip()
        if FIRMA_ACTIVA and not es_doc:
            descripcion += "

— Dr. Williams Barrios
Pediatra y Nutriólogo Clínico
Director Médico – Aesthetic Center"
        return descripcion

    except Exception as e:
        logging.error(f"❌ Error al analizar imagen: {e}")
        return "No pude analizar la imagen correctamente. Por favor, vuelve a intentarlo o agenda una consulta para una valoración más precisa."

# Obtener la URL real del archivo multimedia
def obtener_url_media(media_id: str) -> str:
    url = f"https://graph.facebook.com/v18.0/{media_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    response = requests.get(url, headers=headers)
    return response.json()["url"]

# Enviar respuesta por WhatsApp
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

