from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
import os
import logging

router = APIRouter()

# Token de verificación (debe coincidir exactamente con el que configures en Meta)
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "clinico123")  # Puedes cambiar "clinico123" por el que estés usando

# Endpoint GET para validación del webhook de Meta (muy importante)
@router.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)
    return PlainTextResponse("Forbidden", status_code=403)

# (Opcional) Endpoint POST para recibir mensajes de WhatsApp
@router.post("/webhook")
async def recibir_mensaje(request: Request):
    try:
        data = await request.json()
        logging.info(f"Mensaje recibido: {data}")
        # Aquí puedes procesar el mensaje si lo deseas, por ejemplo, responder con GPT
        return PlainTextResponse("EVENT_RECEIVED", status_code=200)
    except Exception as e:
        logging.error(f"Error procesando el mensaje: {e}")
        return PlainTextResponse("Error interno", status_code=500)
