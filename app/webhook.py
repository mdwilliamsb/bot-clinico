from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
import os
import logging
import requests
from openai import OpenAI

router = APIRouter()

# --- Variables de entorno ---
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "clinico123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Cliente de OpenAI (GPT) ---
gpt = OpenAI(api_key=OPENAI_API_KEY)

# --- Verificación del webhook (GET) ---
@router.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)
    return PlainTextResponse("Forbidden", status_code=403)

# --- Recepción de mensajes (POST) ---
@router.post("/webhook")
async def recibir_mensaje(request: Request):
    try:
        data = await request.json()

        # 📥 Log completo del webhook recibido
        logging.info("📥 Webhook recibido:")
        logging.info(data)

        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if messages:
            mensaje = messages[0]
            texto_usuario = mensaje.get("text", {}).get("body", "")
            numero = mensaje.get("from")

            logging.info(f"✉️ Mensaje recibido de {numero}: {texto_usuario}")

            if texto_usuario and numero:
                respuesta = generar_respuesta_clinica_pro(texto_usuario)
                enviar_respuesta(numero, respuesta)
                logging.info(f"✅ Respuesta enviada a {numero}")
        else:
            logging.warning("⚠️ No se encontró 'messages' en el webhook.")

        return PlainTextResponse("EVENT_RECEIVED", status_code=200)

    except Exception as e:
        logging.error(f"❌ Error procesando el mensaje: {e}")
        return PlainTextResponse("Error interno", status_code=500)

# --- GPT: Generar respuesta médica profesional ---
def generar_respuesta_clinica_pro(mensaje_usuario: str) -> str:
    try:
        prompt = (
            "Eres un asistente médico clínico con conocimientos avanzados en medicina general, pediatría, nutrición, estética, salud mental, urgencias, etc. "
            "Responde de forma clara, profesional y empática al siguiente mensaje recibido por WhatsApp:\n\n"
            f"\"{mensaje_usuario}\"\n\n"
            "Da orientación útil y sugiere valoración presencial si es necesario."
        )

        respuesta = gpt.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un médico experto que responde con empatía y precisión por WhatsApp, sin diagnosticar directamente, pero orientando de forma confiable."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        return respuesta.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"❌ Error al generar respuesta con GPT: {e}")
        return "Lo siento, hubo un error al procesar tu mensaje. Intenta más tarde."

# --- Enviar respuesta a WhatsApp ---
def enviar_respuesta(numero: str, mensaje: str):
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logging.error("❌ WHATSAPP_TOKEN o WHATSAPP_PHONE_NUMBER_ID no están definidos.")
        return

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

    response = requests.post(url, headers=headers, json=payload)
    logging.info(f"📤 Respuesta enviada a {numero}: {response.status_code} - {response.text}")
