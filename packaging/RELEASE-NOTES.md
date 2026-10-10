## 0.4.5 — Preparación privada del instalador de Gentle

- Crea automáticamente una carpeta de preparación nueva dentro del perfil, con propietario igual al usuario actual y ACL privada. No cambia propietario ni permisos de AppData, del perfil o de carpetas existentes.
- Conserva las comprobaciones oficiales de Gentle de ACL, propietarios, ancestros, reparse points e integridad de descargas. No cambia LOCALAPPDATA ni USERPROFILE del proceso.
- Supervisa el proceso del instalador y conserva bootstrap.log; un cierre anticipado se comunica sin esperar una hora.
- Diferencia el fallo posterior install-shell-main de los errores de permisos. No cambia de canal automáticamente ni adopta una instalación incompleta.
- La solución manual de carpeta propia/propietario fue confirmada por el usuario hasta abrir el instalador web. La instalación desde main falló después y su causa sigue pendiente; esta versión no afirma corregirla.

## 0.4.2 — Dependencias automáticas

- Recupera Pi y Gentle incluidos cuando faltan, incluso después de configurar ARISE o mover la carpeta portable.
- No considera instalado un paquete solo por aparecer en los ajustes.
- Instala ScreenView, InputControl, transcripción y Forge con sus dependencias al conectar GitHub. Incluye npm para no requerir Node global.
- Instala las herramientas en una carpeta nueva y comprueba sus catálogos antes de conservar la configuración; mantiene las herramientas desactivadas.

ARISE Assistant 0.4.1

- Paquete completo Windows con modelos Vosk español, Whisper small, Qwen local y llama.cpp CPU.
- Configurar todo desde ZIP: verificación, extracción, rutas automáticas y prueba real del servidor local.
- Cabecera simplificada para dejar más espacio a la conversación.
- Diagnósticos de procesos, pausa de reintentos de Pi y corrección de instalación en Python embebido.
- Conserva modelos personalizados anteriores, datos, permisos del micrófono y configuración del agente.

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

## 0.4.3 — instalación oficial de Gentle y actualización completa

El ZIP completo ahora contiene ARISE-Setup.exe y el paquete de modelos. Configurar ARISE.cmd ejecuta el instalador sobre la instalación existente, conserva los datos y pasa el paquete de modelos al ARISE instalado.

Después de preparar los modelos se abre el instalador oficial de Gentle Shell v4.0.0 (archivo verificado por SHA-256), que permite elegir release estable o último main. Un adaptador observa el resultado y el canal sin cambiar el plan ni el consentimiento del instalador. ARISE adopta la entrada bin.pi del paquete instalado, el directorio de Gentle y su home configurado; el bundle no sustituye ese Pi después. La sesión usa las reglas de carga del propio Gentle para evitar inyectar sus extensiones dos veces. Las interfaces TUI del Gentle oficial siguen sujetas a las capacidades de RPC de esa versión.

Se incluye gh.exe; las descargas de componentes privados pasan por gh api con autenticación en el entorno del proceso. Se reutiliza gh auth login o la credencial GitHub guardada. Se requieren permisos sobre los repositorios privados y conexión a Internet para Gentle y los MCP; el ZIP no contiene claves ni esos repositorios.

La voz local rechaza nombres de herramientas usados como respuesta y respuestas idénticas para preguntas distintas, pide una corrección y, si sigue fallando sin haber ejecutado herramientas, pasa la pregunta a Gentle. Esto no sustituye la calidad de un modelo conversacional mayor. El cierre de Pi espera brevemente su código real de salida antes de informar el fallo.

La prueba de Windows ahora verifica también la conexión al Pi declarado por el paquete usando un home que ya registra Gentle. La instalación interactiva completa de Gentle estable/main en el equipo del usuario requiere comprobación allí; las pruebas automatizadas no inician sesión en proveedores ni repositorios privados.

## 0.4.4 — Forge Voice y perfil local para 8 GB

La opción predeterminada sigue siendo local. Con hasta 10 GB de RAM, el perfil automático elige Vosk y limita contexto/hilos del modelo CPU. No requiere CUDA; Whisper permanece disponible para el perfil estándar. Esto es una cadena STT → modelo de texto → síntesis, no un modelo nativo de voz a voz.

La síntesis local pasa por Forge 0.2 (instalación privada fijada a a1fc2f440c6b3c5288838bbe9fc5e2f1ad3ba6c5). Su reproductor es cancelable y no usa Edge TTS por defecto. Mientras se instala Forge se conserva la voz local de Windows con aviso explícito.

Ajustes ofrece forge-local y forge-openai para audio nativo mediante el puente de Forge. forge-local requiere un servidor de voz a voz compatible con OpenAI Realtime en loopback y un modelo configurado; no usa el Qwen de texto incluido como si fuera un modelo de audio. forge-openai requiere la clave OpenAI y selección explícita. No hay cambio automático a servicios pagados. El ZIP incluye los modelos del perfil local ligero/estándar, no un modelo nativo grande ni un servidor GPU sin verificar.

Pruebas de hardware/modelos nativos externos y llamadas reales al proveedor siguen pendientes. Los tests del protocolo usan WebSocket local y audio sintético. El perfil de 8 GB limita memoria por diseño; falta medir latencia en un Windows físico de esa capacidad.
