import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def generar_dieta(evaluacion):
    prompt = f"Diseña una dieta personalizada para un paciente con: {', '.join(evaluacion.get('enfermedades', []))}."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message["content"]