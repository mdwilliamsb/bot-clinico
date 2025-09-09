
from datetime import datetime, timedelta
import re

def interpretar_fecha_hora(texto_usuario: str) -> datetime:
    texto = texto_usuario.lower()

    # Palabras clave rápidas
    if "pasado mañana" in texto:
        return datetime.now() + timedelta(days=2)
    if "mañana" in texto:
        return datetime.now() + timedelta(days=1)
    if "hoy" in texto:
        return datetime.now()

    # Días de la semana
    dias = {
        "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2,
        "jueves": 3, "viernes": 4, "sábado": 5, "sabado": 5, "domingo": 6
    }
    for dia, indice in dias.items():
        if dia in texto:
            hoy = datetime.now().weekday()
            diferencia = (indice - hoy + 7) % 7
            if diferencia == 0:
                diferencia = 7
            fecha = datetime.now() + timedelta(days=diferencia)
            break
    else:
        fecha = datetime.now()

    # Buscar hora
    hora_match = re.search(r"(?:a las|a la)?\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", texto)
    if hora_match:
        hora = int(hora_match.group(1))
        minuto = int(hora_match.group(2)) if hora_match.group(2) else 0
        meridiano = hora_match.group(3)

        if meridiano == "pm" and hora < 12:
            hora += 12
        if meridiano == "am" and hora == 12:
            hora = 0

        fecha = fecha.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    else:
        fecha = fecha.replace(hour=9, minute=0, second=0, microsecond=0)

    return fecha
