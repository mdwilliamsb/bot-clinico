
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

# --- Recepción de mensajes (POST) ---
@router.post("/webhook")
async def recibir_mensaje(request: Request):
    try:
        data = await request.json()
        logging.info(f"Mensaje recibido: {data}")

        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if messages:
            mensaje = messages[0]
            texto_usuario = mensaje.get("text", {}).get("body", "")
            numero = mensaje.get("from")

            if texto_usuario and numero:
                respuesta = generar_respuesta_clinica_pro(texto_usuario)
                enviar_respuesta(numero, respuesta)

        return PlainTextResponse("EVENT_RECEIVED", status_code=200)
    except Exception as e:
        logging.error(f"Error procesando el mensaje: {e}")
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
        logging.error(f"Error al generar respuesta con GPT: {e}")
        return "Lo siento, hubo un error procesando tu mensaje. Intenta nuevamente más tarde."

# --- Enviar respuesta a WhatsApp ---
def enviar_respuesta(numero: str, mensaje: str):
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logging.error("Faltan WHATSAPP_TOKEN o WHATSAPP_PHONE_NUMBER_ID.")
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
    logging.info(f"Respuesta enviada a {numero}: {response.status_code} - {response.text}")







# # from fastapi import FastAPI
# # from app.webhook import router as webhook_router
# # # Estas importaciones son para tu endpoint /analizar, asegúrate que existan si lo usas.
# # # from app.core.evaluacion import evaluar_paciente
# # # from app.core.motor import responder_gpt

# # app = FastAPI(title="Bot Clínico API", version="1.0.0")

# # # Incluye las rutas definidas en webhook.py (bajo /webhook)
# # app.include_router(webhook_router)

# # @app.get("/", tags=["General"])
# # def home():
# #     """
# #     Endpoint raíz para verificar que el bot está operativo.
# #     """
# #     return {"mensaje": "Bot clínico operativo. El webhook está en /webhook. Usa POST /analizar para enviar texto clínico (si está implementado)."}

# # # Este endpoint es de tu código original, puedes mantenerlo si lo necesitas para pruebas directas.
# # # Si no lo usas, puedes eliminarlo.
# # # @app.post("/analizar", tags=["Análisis (Prueba)"])
# # # def analizar(data: dict):
# # #     """
# # #     Endpoint de prueba para analizar texto clínico directamente.
# # #     Espera un JSON con una clave "texto".
# # #     """
# # #     if "texto" not in data:
# # #         return {"error": "Falta la clave 'texto' en el JSON"}, 400
# # #     try:
# # #         evaluacion = evaluar_paciente(data["texto"])
# # #         resultado = responder_gpt(evaluacion)
# # #         return {"respuesta": resultado}
# # #     except Exception as e:
# # #         # Loggear el error real en un sistema de producción
# # #         print(f"Error en /analizar: {e}")
# # #         return {"error": f"Ocurrió un error procesando la solicitud: {str(e)}"}, 500

# # if __name__ == "__main__":
# #     import uvicorn
# #     # Esto es para correr localmente. Railway usará su propio comando para iniciar la app.
# #     uvicorn.run(app, host="0.0.0.0", port=8000)