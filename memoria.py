
import sqlite3
from datetime import datetime

DB_PATH = "data/memoria.db"

def conectar():
    return sqlite3.connect(DB_PATH)

def inicializar_db():
    with conectar() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telefono TEXT,
                mensaje TEXT,
                timestamp TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nombres (
                telefono TEXT PRIMARY KEY,
                nombre TEXT
            )
        """)

def guardar_mensaje(telefono: str, mensaje: str):
    with conectar() as conn:
        conn.execute("INSERT INTO memoria (telefono, mensaje, timestamp) VALUES (?, ?, ?)",
                     (telefono, mensaje, datetime.now().isoformat()))
        conn.commit()

def recuperar_historial(telefono: str, limite=5):
    with conectar() as conn:
        cursor = conn.execute(
            "SELECT mensaje FROM memoria WHERE telefono = ? ORDER BY timestamp DESC LIMIT ?", (telefono, limite)
        )
        mensajes = cursor.fetchall()
    return "\n".join(m[0] for m in mensajes[::-1]) if mensajes else ""

def actualizar_nombre(telefono: str, mensaje: str):
    posibles = ["soy", "me llamo", "mi nombre es"]
    nombre = None
    for frase in posibles:
        if frase in mensaje.lower():
            partes = mensaje.lower().split(frase)
            if len(partes) > 1:
                nombre = partes[1].strip().split(" ")[0].capitalize()
                break
    if nombre:
        with conectar() as conn:
            conn.execute("REPLACE INTO nombres (telefono, nombre) VALUES (?, ?)", (telefono, nombre))
            conn.commit()

def recuperar_nombre(telefono: str):
    with conectar() as conn:
        cursor = conn.execute("SELECT nombre FROM nombres WHERE telefono = ?", (telefono,))
        fila = cursor.fetchone()
        return fila[0] if fila else None

def detectar_intencion(texto: str):
    texto = texto.lower()
    if any(p in texto for p in ["cita", "agendar", "consulta", "quiero una cita"]):
        return "agendar"
    if any(p in texto for p in ["gracias", "perfecto", "ok"]):
        return "despedida"
    if any(p in texto for p in ["duda", "ayuda", "me siento", "tengo"]):
        return "consulta"
    return "otro"
