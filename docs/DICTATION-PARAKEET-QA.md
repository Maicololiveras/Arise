# Dictado local de ARISE 0.4.32 QA

El micrófono del panel ahora dicta al borrador. Un clic prepara y abre el
micrófono; cuando aparece «Escuchando», el icono cambia a micrófono con flecha
hacia arriba. Otro clic detiene y transcribe. El texto se inserta en el cursor,
sin borrar el borrador ni enviarlo a Pi. Se puede deshacer la inserción.

La primera activación descarga el motor y el modelo (unos 670 MB más el runtime),
con progreso y cancelación. Al terminar pide volver a pulsar para hablar:
la descarga no abre automáticamente el micrófono. En siguientes usos funciona
localmente, sin API key. Usa el dispositivo de entrada predeterminado del sistema,
que puede diferir del seleccionado para la conversación de voz de ARISE.

Esc, el botón Detener, el cambio de chat y la salida cancelan el dictado.
El resultado de una sesión cancelada se descarta. El envío queda suspendido
mientras el dictado está activo; editar el borrador sigue permitido. El límite
es 120 segundos, tras los cuales se transcribe lo grabado. La conversación de
voz existente se pausa durante esta operación y se restablece su estado de
silencio al finalizar. «Hablar» en la bandeja conserva el modo conversacional.

## Motor y distribución

Se adapta el instalador, el worker y la sesión de Gentle Shell v4.5.1, fijados
al commit e8b2814934f98ded9199f49bde8f482c97eece3a. La interfaz de ARISE no
depende de ejecutar `/gentle:voice` en RPC. Los módulos TypeScript se distribuyen
como ESM con tipos borrados; no se requiere compilador TypeScript en el PC.

- Parakeet TDT 0.6B v3 int8, sherpa-onnx 1.13.8 y node-cpal 1.0.0.
- Node >=22; se usa el Node configurado para Pi o el encontrado en PATH.
- Windows x64 requiere Visual C++ Runtime. Windows ARM64 no está soportado.
- Inferencia CPU; no envía audio ni texto a un proveedor de IA.
- Captura al formato del dispositivo y conversión a mono/16 kHz.
- Audio temporal en memoria; captura y reconocimiento en proceso separado.
- Archivos descargados con tamaños y hashes fijados; publicación atómica.
- Almacén propio: `<datos ARISE>/dictation/voice`, separado de Gentle.
- Menú del panel → Reparar dictado local Parakeet invalida los marcadores de
  los componentes fijados y los descarga de nuevo. No toca chats ni memorias.
- Licencias, atribución y limitaciones heredadas: `resources/parakeet/NOTICE.txt`.

## Validación

Pruebas Qt con subproceso real y captura simulada comprueban dos clics,
preservación y deshacer del borrador, ausencia de envío automático, cancelación,
resultados tardíos, cambio de chat, instalación y errores. Los tests adaptados
de Gentle verifican worker/sesión, conversiones, hashes y cierre, con motores
simulados. No son una medición de precisión ni una prueba de micrófono físico.

Antes de considerar estable: ejecutar instalación real y dictado en Windows,
comparar español y términos técnicos contra las mismas grabaciones de Dictto,
medir tiempos y comprobar cierre desde la bandeja. El flujo Android permanece
en su versión anterior: este cambio corresponde al botón del panel de Windows.

## Descargas en redes con proxy

Modelo y runtimes se obtienen de la release fijada
`https://github.com/Maicololiveras/Arise/releases/tag/voice-parakeet-v3-2bda32ec70b0`.
La rama `distribution/parakeet-v3` mantiene el manifest y su publicación.
No se consulta Hugging Face ni npm desde el cliente. La red debe permitir
`github.com` y `release-assets.githubusercontent.com`. Se mantienen TLS y los
hashes originales. La actualización puede volver a preparar componentes de
0.4.31 porque su marcador incluía el origen anterior.
