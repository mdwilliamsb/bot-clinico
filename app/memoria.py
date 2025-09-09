
import sqlite3
import os
from datetime import datetime

# Ruta segura a la base de datos
# DB_PATH = "data/memoria.db"

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "memoria.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

#BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#DB_PATH = os.path.join(BASE_DIR, "data/memoria.db")

# Asegurarse de que la carpeta exista
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)



 
def inicializar_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pacientes (
                numero TEXT PRIMARY KEY,
                nombre TEXT,
                historial TEXT,
                ultima_fecha TEXT
            )
        """)
        conn.commit()
        

# Guardar mensaje recibido
def guardar_mensaje(numero: str, texto: str, nombre: str = None):
    now = datetime.now().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT historial FROM pacientes WHERE numero = ?", (numero,))
        row = cursor.fetchone()
        if row:
            nuevo_historial = (row[0] or "") + f"\n- {texto}"
            cursor.execute("UPDATE pacientes SET historial = ?, ultima_fecha = ? WHERE numero = ?",
                           (nuevo_historial[-3000:], now, numero))
        else:
            cursor.execute("INSERT INTO pacientes (numero, nombre, historial, ultima_fecha) VALUES (?, ?, ?, ?)",
                           (numero, nombre or "", f"- {texto}", now))
        conn.commit()

# Recuperar historial completo
def recuperar_historial(numero: str) -> str:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT historial FROM pacientes WHERE numero = ?", (numero,))
        row = cursor.fetchone()
        return row[0] if row else ""

# Recuperar nombre si existe
def recuperar_nombre(numero: str) -> str:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM pacientes WHERE numero = ?", (numero,))
        row = cursor.fetchone()
        return row[0] if row and row[0] else None

# Guardar nombre si se detecta por mensaje tipo "Soy Ana"
def actualizar_nombre(numero: str, texto: str):
    if "soy " in texto.lower():
        probable_nombre = texto.lower().split("soy ")[-1].split(" ")[0].capitalize()
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE pacientes SET nombre = ? WHERE numero = ?", (probable_nombre, numero))
            conn.commit()

# Detección básica de intención
def detectar_intencion(texto: str) -> str:
    t = texto.lower()
    if any(p in t for p in ["cita", "agendar", "consulta", "disponible", "quiero ver", "puedo ir"]):
        return "agendar"
    elif any(p in t for p in ["precio", "cuánto", "costo", "cuesta"]):
        return "costos"
    elif t in ["hola", "buenos días", "buenas tardes", "buenas noches"]:
        return "saludo"
    return "consulta"

# Inicializar al importar
init_db()
