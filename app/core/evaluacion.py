import re

def evaluar_paciente(texto_usuario):
    texto = texto_usuario.lower()
    enfermedades = [
        "diabetes", "hipertensión", "hipotiroidismo", "enfermedad renal", "artritis", 
        "lupus", "resistencia a la insulina", "intestino irritable", "intestino permeable",
        "hígado graso", "síndrome metabólico", "obesidad", "sobrepeso", "colitis", 
        "fatiga crónica", "ansiedad", "depresión"
    ]
    enfermedades_detectadas = [e for e in enfermedades if e in texto]
    farmacos_suplementos = [
        "levotiroxina", "metformina", "insulina", "statina", "omega 3", "magnesio", 
        "vitamina d", "probióticos", "zinc", "hierro", "berberina", "coenzima q10",
        "melatonina", "calcio", "vitamina c", "vitamina b12", "ashwagandha"
    ]
    medicamentos_detectados = [m for m in farmacos_suplementos if m in texto]
    edad = None
    peso = None
    talla = None
    edad_busqueda = re.search(r"(tengo|edad)\s*(\d{1,2})", texto)
    if edad_busqueda:
        edad = int(edad_busqueda.group(2))
    peso_match = re.search(r"peso\s*(\d{2,3})\s*kg", texto)
    talla_match = re.search(r"mido\s*(\d(?:[.,]\d{1,2})?)", texto)
    if peso_match:
        peso = int(peso_match.group(1))
    if talla_match:
        talla = float(talla_match.group(1).replace(",", "."))
    imc = round(peso / (talla ** 2), 2) if peso and talla else None
    return {
        "edad": edad,
        "peso": peso,
        "talla": talla,
        "imc": imc,
        "enfermedades": enfermedades_detectadas,
        "medicamentos_suplementos": medicamentos_detectados,
        "texto_original": texto_usuario
    }