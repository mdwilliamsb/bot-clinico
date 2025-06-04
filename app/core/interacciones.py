def analizar_interacciones(texto_usuario):
    if "levotiroxina" in texto_usuario and "calcio" in texto_usuario:
        return "Levotiroxina y calcio no deben tomarse juntos. Separar al menos 4 horas."
    return "Sin interacciones críticas detectadas."