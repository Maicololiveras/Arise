# ARISE 0.4.27 QA

- Android Companion 0.1.1 QA usa el primer fotograma del orbe original, igual que la identidad de escritorio, en launcher, pantalla inicial y burbuja.
- Consulta de nuevas versiones Android al abrir la pantalla de configuración y mediante botón; la descarga exige confirmación y Android controla la instalación.
- Metadatos públicos acotados, URL de APK limitada a releases del repositorio y publicación versionada antes de anunciar actualizaciones.
- Respeta las barras del sistema en la configuración Android. Firma de depuración y migración desde APK anteriores siguen siendo limitaciones de QA; no se promete actualización en sitio ni ausencia de avisos de Play Protect.

# ARISE 0.4.26 QA

- La finalización de una terminal delegada reactiva al agente inactivo para consultar y verificar el resultado, sin esperar otra pregunta del usuario.
- Si el agente sigue trabajando, el aviso se encola mediante el protocolo prompt/followUp de Pi. Se comprueba la recepción; los errores se muestran y no provocan reenvíos automáticos.
- Evita avisos duplicados y conserva el resultado en el chat de origen. No reconecta sesiones ni reactiva tareas tras cambiar de chat, detener o revocar ejecución local.
- Reproducido el fallo anterior y comprobada la reactivación con Pi/Gentle real y proveedor simulado. Pendiente prueba en el PC con documento real y proveedor del usuario.

# ARISE 0.4.25 QA

- QR en Ajustes > Conexiones, celular y recordatorios > Celular para descargar el APK Android QA, con opciones de abrir y copiar el enlace.
- Publicación del APK en una release Android QA tras pasar pruebas, lint y compilación. El QR es de descarga y no contiene credenciales ni códigos de vinculación.
- Se conserva el vínculo privado mediante Tailscale y código temporal. El APK no es compatible con iPad; se mantiene el acceso web.
- APK firmado para depuración: las siguientes compilaciones pueden requerir reinstalación. Prueba física en Android pendiente.

# ARISE 0.4.24 QA

- Gentle Shell 4.5.0, Pi 1.4.0 y Gentle AI 4.3.1; instalador oficial actualizado y verificado por SHA-256.
- Adaptación del panel unificado de perfiles y modelos, conservando las confirmaciones de Gentle.
- Alternativa en Ajustes para abrir la TUI del binario Gentle AI e instalar Shell. Conserva el motor actual de ARISE.
- Limitación: el Shell instalado mediante la TUI se verifica como CLI independiente; no se adopta automáticamente como motor RPC de ARISE porque el supervisor nativo no transmite su contexto de permisos y herramientas.
- Incluye funciones experimentales de conexiones, recordatorios y puente móvil de QA. Requieren configuración y autorización explícitas; no se han verificado cuentas externas ni dispositivos móviles reales.
- Pruebas automatizadas y compilación Windows obligatorias antes de publicar. Pendiente probar la instalación nativa por TUI en los PCs afectados; no se da por resuelto su fallo previo.

# ARISE 0.4.23 QA

- Comandos de la sesión en una ventana compacta con lista desplazable y búsqueda por nombre o descripción.
- Búsqueda sin distinguir mayúsculas ni acentos; Enter ejecuta la selección, Esc cierra y las flechas permiten recorrer la lista enfocada.
- La ventana se cierra al recargar/cambiar el chat; resultados de catálogos anteriores no se muestran en la nueva ventana.
- Se conserva la ejecución y las confirmaciones del runtime.

# ARISE 0.4.22 QA

- Voz OpenAI/Gemini: aceptación inmediata de tareas, consulta de estado y corrección/cancelación por identificador del chat.
- Una nueva petición no modifica silenciosamente la tarea activa; los resultados tardíos no se entregan en otro chat.
- Se conserva la ruta de voz local y las aprobaciones existentes. Calidad de audio y proveedores reales pendientes de prueba en PC.
- Corregida la versión del instalador y del icono a 0.4.22; prueba temprana de coherencia entre aplicación, instalador, bundle y notas.

# ARISE 0.4.21 QA

- Avisos de conexión Pi/Gentle y carga de herramientas en una barra discreta bajo el campo de escritura, fuera del historial.
- Una línea de altura fija, texto completo al pasar el cursor y disponible para accesibilidad; no mueve el chat ni roba foco.
- La barra se limpia al cambiar de chat; errores y confirmaciones mantienen su presentación visible.

# ARISE 0.4.20 QA

- Gentle Shell 4.3.0 y su instalador oficial fijados; Pi se mantiene en 1.2.0, compatible con el mínimo declarado.
- Conserva la configuración aislada de Gentle 4.3 al reutilizar su entorno; los entornos vinculados y personalizados mantienen sus reglas.
- Mantiene el host RPC interactivo, las confirmaciones, el aislamiento por chat y la parada de ARISE.
- Gentle 4.3 incorpora temporales por sesión, registro de artefactos y Gentle AI 4.2.0. ARISE no borra esos directorios por su cuenta.
- Requiere validar en CI la compilación e instalación Windows; no certifica el fallo entry-storage de otros PCs.

# ARISE 0.4.19 QA

- Actividad compacta a la izquierda y Detener a la derecha; más espacio para el chat.
- Alt+Q recupera el último mensaje sin enviarlo ni sobrescribir el borrador.
- Delegación explícita en terminal Gentle por chat, con consentimiento, resultados propios y cancelación.
- Instalador: recorrido de antecesores protegido contra ciclos/PID reutilizados, consultas acotadas y diagnóstico de parada.
- Validación nativa de instalación y terminal Windows pendiente de CI y prueba en PC; detalles en docs/QA-0.4.19.md.

# ARISE 0.4.18 QA

- Ventana de actualización con novedades desplazables y botones siempre fuera del área de scroll.
- Tamaño inicial adaptado al espacio disponible; texto ajustado al ancho, sin scroll horizontal.
- Instalar requiere confirmación explícita; Cerrar, Más tarde y Escape no instalan.
- Interfaz Qt comprobada a 340 × 440 en Linux; validación nativa en Windows pendiente de CI y prueba del usuario.

# ARISE 0.4.17 QA

- Recupera el entorno privado existente de Gentle y usa su Node, Pi y carpeta de agente, sin consultar pnpm global.
- Verifica la versión activa y rechaza instalaciones incompletas o ambiguas; conserva la comprobación nativa de Gentle y la verificación RPC antes de adoptar.
- Transcripción instala MCP 1.x en su Python privado, compatible con mcp.server.fastmcp.
- Pendientes: instalación inicial que falla en entry-storage y prueba física de micrófono -9996 en el PC afectado. Reutilizar requiere una instalación de Gentle completa.

# ARISE 0.4.16 · QA

- PowerShell: validación de pnpm transportada con EncodedCommand; los errores de E/S se clasifican sin exponer stderr. Las pruebas Windows invocan ahora Node y PowerShell como producción.
- Forge: comprueba el adaptador Edge real; evita el aviso incorrecto basado en el puente antiguo.
- Audio: identifica entrada/salida y código numérico de PortAudio; sin cambiar dispositivos o sustituir la voz.
- Transcripción: identifica el módulo Python ausente, sin mostrar el traceback.
- La causa final en el PC afectado requiere revalidación; no se anuncia resuelta por las pruebas de CI.

# ARISE 0.4.15 · QA

- Gentle: admite la junction local conocida de pnpm v11 y comprueba el destino y sus antecesores; rechaza otros enlaces y permisos de escritura no confiables.
- Instalación automática de herramientas independiente: una transcripción fallida no descarta ScreenView, InputControl ni Forge.
- Audio: distingue errores al abrir dispositivos y modelos Vosk ausentes o incompletos. No cambia la voz ni descarga modelos sin selección.
- Pendiente: prueba en el PC personal afectado. No se ha confirmado la causa de su fallo de audio.

# ARISE 0.4.14 · QA

- Sesión persistente entre mensajes y ajustes de voz; cambio de chat con historial propio y cierre controlado.
- Capacidades reales visibles, autorización local por chat y ejecución mediante Gentle, sin activar escritorio.
- Creación y lectura DOCX sin escritorio, con contenido verificado y plantilla DOCX opcional en modo añadir.
- Actividad de ARISE: cuadro discreto y plegable, estados reales de herramientas/subagentes, modelo cuando se informa y progreso sin porcentajes inventados. No muestra razonamiento privado.
- Parada conserva revocación de manos/ojos; cierra subagentes de fondo sin reiniciarlos automáticamente.

Pruebas locales con Pi/Gentle reales y modelo simulado, DOCX real y UI Qt. Pendiente validación física de Windows, proveedor real y plantilla WEG del usuario. Detalles: docs/QA-ORCHESTRATOR-0.4.14.md.
