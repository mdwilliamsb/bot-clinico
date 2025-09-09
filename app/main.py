from fastapi import FastAPI
from app.webhook import router as webhook_router  # ✅ Línea corregida

app = FastAPI(title="Bot Clínico API", version="1.0.0")

app.include_router(webhook_router)

@app.get("/", tags=["General"])
def home():
    return {
        "mensaje": "Bot clínico operativo. El webhook está en /webhook."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
