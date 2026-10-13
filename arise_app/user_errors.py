"""Short recovery guidance; no retry of an ambiguous operation."""
def friendly_error(message):
    message=str(message)
    if '503' in message or 'Service Unavailable' in message:
        return 'El servicio de IA no está disponible temporalmente (503). No se reenvió el mensaje. Espera y comprueba el estado de la tarea antes de volver a enviarlo.'
    if 'timeout' in message.lower() or 'tiempo' in message.lower() or 'no responde' in message.lower():
        return 'No se pudo confirmar la respuesta. El mensaje podría haberse recibido; no se reenviará automáticamente. Revisa la tarea antes de reintentar.'
    return message[:600]
