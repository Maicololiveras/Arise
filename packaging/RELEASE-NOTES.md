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
