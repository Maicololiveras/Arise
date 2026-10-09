ARISE Assistant 0.4.0

- Orbe persistente; doble clic abre el chat y clic sencillo lo oculta.
- El panel acompaña al orbe, recuerda su ubicación y se oculta tras 60 segundos sin interacción.
- Activación por voz sin abrir el panel de chat.
- Voz local con captura continua, interrupción de audio y correcciones en la misma sesión de Gentle Shell. Vosk/Whisper + Windows SAPI/Piper; no requiere una API de voz. La latencia depende del hardware y del modelo del agente. Auriculares recomendados para evitar eco; no incluye cancelación acústica de eco.
- Interlocutor local configurable (por defecto LM Studio en localhost:1235), contexto por chat y delegación concurrente a Gentle. Requiere un servidor/modelo cargado; sin él usa voz directa con Gentle.
- Preguntas select/input/confirm de Gentle pueden responderse por voz. Las aprobaciones de envío de Gmail conservan su revisión visual.
- Consulta de versiones en main, novedades, instalación consentida y descarga verificada por SHA-256.
- Launcher externo y cierre coordinado de UI, daemon, Pi y procesos hijos antes de reemplazar los archivos.
- Conserva chats, memoria, modelos de usuario y configuración al reinstalar.
- Compatible con repositorios privados: credencial GitHub protegida por Windows o sesión existente de gh.
- Descarga y configura ScreenView (ojos) e InputControl (manos) con un runtime Python incluido. Los repos privados requieren acceso a GitHub una vez.
