# Descargas desde Ajustes

En **Herramientas** se puede descargar/reparar Forge, ScreenView e InputControl por separado o las tres juntas. El instalador consulta los manifiestos de `Maicololiveras/Arise`, rama `herramientas`, y obtiene únicamente los binarios publicados. No necesita sesión GitHub. Transcripción continúa siendo opcional y privada, con su botón propio.

En **Descargas** se puede instalar Vosk español, Whisper small, Piper español o Qwen con llama.cpp; también todos los modelos juntos. Las rutas se guardan automáticamente. Piper usa su motor directamente y no necesita el puente de voz Forge. Instalar Vosk no reemplaza el motor Whisper que el usuario haya elegido.

Las descargas grandes usan las versiones y SHA-256 del paquete offline existente. Cada instalación usa una carpeta nueva; los modelos y catálogos se comprueban antes de confirmar su configuración. Un fallo restaura los ajustes anteriores. Los componentes no seleccionados conservan su configuración. Reintentar inicia una descarga nueva; todavía no se reanudan archivos parciales.

Los manifiestos públicos de herramientas están pendientes hasta publicar sus binarios. Los workflows privados necesitan `TOOLS_PUBLISH_TOKEN` con escritura de contenido limitada a Arise. Un manifiesto pendiente muestra un error recuperable y conserva la instalación existente. El Forge público actual no incluye el puente de voz; se conserva el puente anterior si existe.

Esta preparación no modifica el instalador QA 0.4.9 ya publicado. Requiere una nueva compilación/versionado antes de distribuirse como actualización. Validación local: pruebas de selección individual, descargas corruptas, origen, rutas ZIP, rollback de modelos y MCP, conservación de voz y acciones Qt. La interfaz se recorrió con Qt offscreen en Linux; la ejecución de los binarios descargados debe validarse en Windows cuando estén publicados.
