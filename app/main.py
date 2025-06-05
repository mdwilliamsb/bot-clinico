from fastapi import FastAPI
from app.webhook import router as webhook_router

app = FastAPI(title="Bot Clínico API", version="1.0.0")

# Registrar las rutas del webhook (GET y POST en /webhook)
app.include_router(webhook_router)

# Ruta raíz para verificar funcionamiento del bot
@app.get("/", tags=["General"])
def home():
    return {
        "mensaje": "Bot clínico operativo. El webhook está en /webhook."
    }

# Solo para correr localmente (Railway no necesita esto)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
