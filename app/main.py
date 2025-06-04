from fastapi import FastAPI
from app.webhook import router as webhook_router
from app.core.evaluacion import evaluar_paciente
from app.core.motor import responder_gpt

app = FastAPI()

app.include_router(webhook_router)

@app.get("/")
def home():
    return {"mensaje": "Bot clínico operativo. Usa POST /analizar para enviar texto clínico."}

@app.post("/analizar")
def analizar(data: dict):
    evaluacion = evaluar_paciente(data["texto"])
    resultado = responder_gpt(evaluacion)
    return {"respuesta": resultado}