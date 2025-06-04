from fastapi import Request, APIRouter
from fastapi.responses import PlainTextResponse
import os
import requests
from app.core.evaluacion import evaluar_paciente
from app.core.motor import responder_gpt

router = APIRouter()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "clinico123")

# ✅ Verificación del Webhook por Meta (GET)
@router.get("/webhook")
def verificar_webhook(hub_mode: str = "", hub_verify_token: str = "", hub_challenge: str = ""):
    print("RECIBIDO:", hub_verify_token, "| ESPERADO:", VERIFY_TOKEN)
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge, status_code=200)
    return {"status": "forbidden"}

# ✅ Recepción de mensajes de WhatsApp (POST)
@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    data = await request.json()
    try:
        mensaje_usuario = data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
        numero = data["entry"][0]["changes"][0]["value"]["messages"][0]["from"]

        print("Mensaje recibido:", mensaje_usuario)

        evaluacion = evaluar_paciente(mensaje_usuario)
        respuesta = responder_gpt(evaluacion)

        enviar_mensaje_whatsapp(numero, respuesta)

        return {"status": "ok"}
    except Exception as e:
        print("Error procesando el webhook:", e)
        return {"status": "error", "detail": str(e)}

# ✅ Envío de respuesta vía API de WhatsApp
def enviar_mensaje_whatsapp(numero_destino, mensaje):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": mensaje}
    }
    r = requests.post(url, json=payload, headers=headers)
    print("Enviado a WhatsApp:", r.status_code, r.text)
