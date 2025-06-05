from fastapi import FastAPI
from app.webhook import router as webhook_router
# Estas importaciones son para tu endpoint /analizar, asegúrate que existan si lo usas.
# from app.core.evaluacion import evaluar_paciente
# from app.core.motor import responder_gpt

app = FastAPI(title="Bot Clínico API", version="1.0.0")

# Incluye las rutas definidas en webhook.py (bajo /webhook)
app.include_router(webhook_router)

@app.get("/", tags=["General"])
def home():
    """
    Endpoint raíz para verificar que el bot está operativo.
    """
    return {"mensaje": "Bot clínico operativo. El webhook está en /webhook. Usa POST /analizar para enviar texto clínico (si está implementado)."}

# Este endpoint es de tu código original, puedes mantenerlo si lo necesitas para pruebas directas.
# Si no lo usas, puedes eliminarlo.
# @app.post("/analizar", tags=["Análisis (Prueba)"])
# def analizar(data: dict):
#     """
#     Endpoint de prueba para analizar texto clínico directamente.
#     Espera un JSON con una clave "texto".
#     """
#     if "texto" not in data:
#         return {"error": "Falta la clave 'texto' en el JSON"}, 400
#     try:
#         evaluacion = evaluar_paciente(data["texto"])
#         resultado = responder_gpt(evaluacion)
#         return {"respuesta": resultado}
#     except Exception as e:
#         # Loggear el error real en un sistema de producción
#         print(f"Error en /analizar: {e}")
#         return {"error": f"Ocurrió un error procesando la solicitud: {str(e)}"}, 500

if __name__ == "__main__":
    import uvicorn
    # Esto es para correr localmente. Railway usará su propio comando para iniciar la app.
    uvicorn.run(app, host="0.0.0.0", port=8000)