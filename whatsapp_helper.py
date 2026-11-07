import urllib.parse
import re


def limpiar_telefono(telefono: str, codigo_pais: str = "+591") -> str:
    """
    Limpia el número de teléfono removiendo espacios, guiones y paréntesis.
    Si no tiene prefijo de país (+), le añade el código predeterminado.
    """
    solo_numeros = re.sub(r"[^\d+]", "", telefono.strip())
    if not solo_numeros.startswith("+"):
        # Quitar ceros a la izquierda si los hubiera
        solo_numeros = solo_numeros.lstrip("0")
        prefijo = codigo_pais.replace("+", "")
        if not solo_numeros.startswith(prefijo):
            solo_numeros = f"{prefijo}{solo_numeros}"
    else:
        solo_numeros = solo_numeros.replace("+", "")
    return solo_numeros


def formatear_mensaje_ausencia(
    plantilla: str,
    tutor: str,
    estudiante: str,
    fecha: str,
    institucion: str = "Colegio"
) -> str:
    """
    Reemplaza variables dinámicas en la plantilla de mensaje.
    """
    try:
        mensaje = plantilla.format(
            tutor=tutor,
            estudiante=estudiante,
            fecha=fecha,
            institucion=institucion
        )
    except (KeyError, IndexError):
        # Si la plantilla del usuario tiene errores de formato, usar mensaje por defecto
        mensaje = (
            f"Estimado(a) {tutor}: Le informamos de la institución {institucion} "
            f"que su hijo(a) {estudiante} registró INASISTENCIA el día {fecha}. "
            f"Por favor comunicarse para justificar la falta."
        )
    return mensaje


def generar_enlace_whatsapp(telefono: str, mensaje: str, codigo_pais: str = "+591") -> str:
    """
    Genera el enlace directo para abrir WhatsApp en Android/Web/Desktop.
    """
    telefono_limpio = limpiar_telefono(telefono, codigo_pais)
    mensaje_codificado = urllib.parse.quote(mensaje)
    return f"https://wa.me/{telefono_limpio}?text={mensaje_codificado}"