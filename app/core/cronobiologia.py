def sugerir_horario_optimo(lista_meds):
    horarios = {
        "levotiroxina": "6:30 AM en ayunas",
        "metformina": "con desayuno y cena",
        "melatonina": "30 min antes de dormir"
    }
    resultado = []
    for m in lista_meds:
        hora = horarios.get(m.lower(), "Horario no específico.")
        resultado.append(f"{m}: {hora}")
    return "\n".join(resultado)