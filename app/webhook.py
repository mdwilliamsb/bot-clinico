from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
import os
import logging
import requests
from openai import OpenAI

router = APIRouter()

# --- Configuración de entorno ---
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "clinico123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Cliente GPT ---
gpt = OpenAI(api_key=OPENAI_API_KEY)

# --- Verificación del Webhook (GET) ---
@router.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)
    return PlainTextResponse("Forbidden", status_code=403)

# --- Recepción de mensajes (POST) con logs mejorados ---
@router.post("/webhook")
async def recibir_mensaje(request: Request):
    try:
        data = await request.json()

        # 🔍 Mostrar el contenido completo del webhook recibido
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

        return PlainTextResponse("EVENT_RECEIVED", status_code=200)
    except Exception as e:
        logging.error(f"❌ Error procesando el mensaje: {e}")
        return PlainTextResponse("Error interno", status_code=500)

# --- GPT: Genera respuesta clínica profesional ---
def generar_respuesta_clinica_pro(mensaje_usuario: str) -> str:
    try:
        prompt = (
            "Eres un asistente médico clínico con conocimientos avanzados en todas las áreas de la salud: "
            "medicina general, nutrición, pediatría, ginecología, medicina estética, endocrinología, salud mental, medicina del deporte, urgencias, etc. "
            "Responde al siguiente mensaje con claridad, calidez y evidencia médica. Si detectas síntomas graves, sugiere acudir a un centro médico. "
            "Si es una duda estética, nutricional o leve, ofrece una orientación útil, práctica y profesional.\n\n"
            f"Mensaje del paciente: \"{mensaje_usuario}\"\n\n"
            "Tu respuesta debe ser médica, confiable y adaptada al paciente que escribe por WhatsApp."
        )

        respuesta = gpt.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un médico clínico multidisciplinario que responde por WhatsApp con un lenguaje profesional, empático y humano. "
                        "Tu objetivo es ayudar, orientar, tranquilizar o alertar según sea el caso, sin diagnosticar directamente. "
                        "Eres extremadamente claro y sabes comunicarte con cualquier tipo de paciente."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.6
        )

        return respuesta.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"❌ Error generando respuesta con GPT: {e}")
        return "Lo siento, hubo un error procesando tu mensaje. Intenta nuevamente más tarde."

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
