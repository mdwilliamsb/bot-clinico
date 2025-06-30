
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
import os
import logging
import requests
import json
from openai import OpenAI
import base64

# Configuración inicial
logging.basicConfig(level=logging.INFO)
router = APIRouter()

# Variables de entorno
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "clinico123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NUMERO_DOCTOR = os.getenv("NUMERO_DOCTOR", "5217221623550")
FIRMA_ACTIVA = os.getenv("FIRMA_ACTIVA", "true").lower() == "true"

# Cliente OpenAI
gpt = OpenAI(api_key=OPENAI_API_KEY)

# Cargar comandos externos
def cargar_comandos():
    path = "./app/contexto/comandos.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

COMANDOS = cargar_comandos()

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

# Filtro de mensajes triviales
def es_mensaje_irrelevante(texto: str) -> bool:
    texto = texto.strip().lower()
    return texto in ["hola", "ok", "gracias", "👍", "👌", "🙌", "🙋‍♂️"] or len(texto) < 4

# --- GET: Verificación del webhook
@router.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)
    return PlainTextResponse("Forbidden", status_code=403)

# --- POST: Recepción de mensajes
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
            if texto.lower() in COMANDOS:
                prompt = COMANDOS[texto.lower()]
                respuesta = responder_por_comando(prompt, numero)
            elif es_mensaje_irrelevante(texto):
                return PlainTextResponse("EVENT_RECEIVED", status_code=200)
            else:
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
        return PlainTextResponse("Error interno", status_code=500)

# GPT: Comando personalizado
def responder_por_comando(prompt: str, numero: str) -> str:
    chat = gpt.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Actúas como el Dr. Williams Barrios."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5
    )
    return chat.choices[0].message.content.strip()

# GPT: Texto libre personalizado
def generar_respuesta_personalizada(texto_usuario: str, numero: str) -> str:
    es_doc = numero == NUMERO_DOCTOR
    prompt = f"""
Actúa como el Dr. Williams Barrios, médico clínico y estético en Aesthetic Center.
Guía cetogénica:
{GUIA_KETO}

Horarios:
{HORARIOS}

Mensaje recibido: "{texto_usuario}"
Tu respuesta debe:
- Ser empática y precisa
- Orientar sin diagnosticar
- Derivar si es administrativo
- Recomendar consulta si hay síntomas
"""
    chat = gpt.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Eres el Dr. Williams Barrios, médico humano, cálido, profesional."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.6
    )
    respuesta = chat.choices[0].message.content.strip()
    if FIRMA_ACTIVA and not es_doc:
        respuesta += "\n\n— Dr. Williams Barrios\nDirector Médico – Aesthetic Center"
    return respuesta

# GPT-4 Vision: Imagen clínica
def analizar_imagen_clinica(media_id: str, numero: str) -> str:
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
                    "Eres el Dr. Williams Barrios. Analiza imágenes médicas con responsabilidad. "
                    "Nunca das diagnóstico definitivo. Sugieres consulta presencial."
                )},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": (
                            "Describe la imagen clínicamente. Expón posibles causas comunes, sin asegurar diagnóstico. "
                            "Recomienda consulta para evaluación presencial."
                        )},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
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
        return "No pude analizar la imagen. ¿Podrías intentar enviarla de nuevo o acudir a consulta presencial?"

# Descargar URL de imagen original desde Meta API
def obtener_url_media(media_id: str) -> str:
    url = f"https://graph.facebook.com/v18.0/{media_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    response = requests.get(url, headers=headers)
    return response.json()["url"]

# Enviar respuesta final por WhatsApp
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
