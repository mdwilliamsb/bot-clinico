from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
import os
import logging
import requests
from openai import OpenAI

# ✅ Activar logs para Railway
logging.basicConfig(level=logging.INFO)

router = APIRouter()

# --- Variables de entorno ---
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "clinico123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Cliente OpenAI GPT ---
gpt = OpenAI(api_key=OPENAI_API_KEY)

# --- Verificación de webhook (GET) ---
@router.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)
    return PlainTextResponse("Forbidden", status_code=403)

# --- Webhook de recepción (POST) ---
@router.post("/webhook")
async def recibir_mensaje(request: Request):
    try:
        data = await request.json()

        # Logs visibles
        print("📥 JSON recibido:")
        print(data)
        logging.info("📥 Webhook recibido:")
        logging.info(data)

        entry = data.get("entry", [])
        if not entry:
            logging.info("⚠️ No se encontró 'entry'")
            return PlainTextResponse("EVENT_RECEIVED", status_code=200)

        changes = entry[0].get("changes", [])
        if not changes:
            logging.info("⚠️ No se encontró 'changes'")
            return PlainTextResponse("EVENT_RECEIVED", status_code=200)

        value = changes[0].get("value", {})
        logging.info("🔎 VALUE recibido:")
        logging.info(value)

        messages = value.get("messages", [])

        if not messages:
            logging.info("📌 Evento recibido, pero no es un mensaje nuevo. (Probablemente un status)")
            return PlainTextResponse("EVENT_RECEIVED", status_code=200)

        mensaje = messages[0]
        texto_usuario = mensaje.get("text", {}).get("body", "")
        numero = mensaje.get("from")

        logging.info(f"✉️ Mensaje recibido de {numero}: {texto_usuario}")

        if texto_usuario and numero:
            # ✅ Usar GPT para generar la respuesta clínica
            respuesta = generar_respuesta_clinica_pro(texto_usuario)
            enviar_respuesta(numero, respuesta)
            logging.info(f"✅ Respuesta enviada a {numero}")
        else:
            logging.warning("⚠️ Texto o número no válidos.")

        return PlainTextResponse("EVENT_RECEIVED", status_code=200)

    except Exception as e:
        logging.error(f"❌ Error procesando el webhook: {e}")
        return PlainTextResponse("Error interno", status_code=500)

# --- GPT: Genera respuesta clínica profesional ---
def generar_respuesta_clinica_pro(mensaje_usuario: str) -> str:
    try:
        prompt = (
            "Eres un asistente médico clínico con conocimientos avanzados en medicina general, nutrición, pediatría, ginecología, medicina estética, salud mental y urgencias. "
            "Responde con claridad, empatía y evidencia médica al siguiente mensaje recibido por WhatsApp:\n\n"
            f"\"{mensaje_usuario}\"\n\n"
            "Tu respuesta debe ser confiable, sin diagnosticar directamente. Si es necesario, sugiere acudir a consulta médica."
        )

        respuesta = gpt.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un médico clínico experto que responde por WhatsApp con precisión, humanidad y lenguaje claro. "
                        "Tu prioridad es orientar bien, sin dar diagnósticos definitivos, y ser muy útil para el paciente."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        return respuesta.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"❌ Error al generar respuesta con GPT: {e}")
        return "Lo siento, hubo un error al procesar tu mensaje. Intenta nuevamente más tarde."

# --- Enviar respuesta por WhatsApp ---
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
