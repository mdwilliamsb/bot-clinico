from app.core.dieta import generar_dieta
from app.core.ejercicio import prescribir_ejercicio
from app.core.interacciones import analizar_interacciones
from app.core.cronobiologia import sugerir_horario_optimo

def responder_gpt(evaluacion):
    dieta = generar_dieta(evaluacion)
    ejercicio = prescribir_ejercicio(evaluacion)
    texto_meds = " ".join(evaluacion.get("medicamentos_suplementos", []))
    interacciones = analizar_interacciones(texto_meds)
    horario_optimo = sugerir_horario_optimo(evaluacion.get("medicamentos_suplementos", []))
    return f'''
EVALUACION CLINICA
Edad: {evaluacion.get('edad')}, Peso: {evaluacion.get('peso')} kg, Talla: {evaluacion.get('talla')} m, IMC: {evaluacion.get('imc')}
Condiciones: {', '.join(evaluacion.get('enfermedades', []))}

PLAN DE DIETA PERSONALIZADA
{dieta}

PLAN DE EJERCICIO
{ejercicio}

INTERACCIONES DETECTADAS
{interacciones}

HORARIO RECOMENDADO
{horario_optimo}
    '''.strip()