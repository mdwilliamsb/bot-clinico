from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
import os
import logging
import requests
from openai import OpenAI

# ✅ Activar logs en consola
logging.basicConfig(level=logging.INFO)

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

        # Logs forzados para depuración
        print("📥 JSON recibido:")
        print(data)
        logging.info("📥 Webhook recibido:")
        logging.info(data)

        entry = data.get("entry", [])
        if not entry:
            print("⚠️ Falta 'entry'")
            return PlainTextResponse("EVENT_RECEIVED", status_code=200)

        changes = entry[0].get("changes", [])
        if not changes:
            print("⚠️ Falta 'changes'")
            return PlainTextResponse("EVENT_RECEIVED", status_code=200)

        value = changes[0].get("value", {})
        print("🔎 VALUE recibido:")
        print(value)

        messages = value.get("messages", [])
        if not messages:
            print("⚠️ No se encontró 'messages'")
            return PlainTextResponse("EVENT_RECEIVED", status_code=200)

        mensaje = messages[0]
        texto_usuario = mensaje.get("text", {}).get("body", "")
        numero = mensaje.get("from")

        print(f"✉️ Mensaje recibido de {numero}: {texto_usuario}")

        if texto_usuario and numero:
            # 🔁 Respuesta de prueba (no GPT)
            respuesta = f"Recibido: '{texto_usuario}' - gracias por escribir."
            enviar_respuesta(numero, respuesta)
            print(f"✅ Respuesta enviada a {numero}")
        else:
            print("⚠️ Texto o número vacío")

        return PlainTextResponse("EVENT_RECEIVED", status_code=200)

    except Exception as e:
        print(f"❌ Error procesando el webhook: {e}")
        return PlainTextResponse("Error interno", status_code=500)

# --- Enviar respuesta a WhatsApp ---
def enviar_respuesta(numero: str, mensaje: str):
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        print("❌ WHATSAPP_TOKEN o WHATSAPP_PHONE_NUMBER_ID no están definidos.")
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
    print(f"📤 Respuesta enviada a {numero}: {response.status_code} - {response.text}")
