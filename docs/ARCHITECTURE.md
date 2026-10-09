# ARISE runtime

La esfera conserva la identidad ARISE del renderer QPainter de praxisgenai-harness. El atlas contiene 24 imágenes generadas de ese renderer; no usa WebGL. Panel y ajustes son widgets Qt.

```mermaid
flowchart TD
    U[Panel y orbe Qt] -->|HTTP autenticado local| D[Daemon Python]
    R[Supervisor Rust] -->|Inicia y espera| D
    W[Gateway web privado] --> D
    D --> V[Audio y proveedores]
    D --> P[Pi con Gentle Shell]
    P -->|Extensión ARISE| C[Catálogo de capacidades]
    C --> M[MCP de escritorio]
    C --> G[Gmail y archivos]
```

`arise-host` es un supervisor pequeño de procesos, no un segundo motor de agentes. El engine Python posee el lock de instancia, audio, almacenamiento, tareas y el puente autenticado. El cliente Qt no mantiene herramientas ni claves. El motor Pi posee el bucle de ejecución y carga las extensiones de Gentle Shell.

En desarrollo el launcher inicia el daemon Python directamente. El paquete compilado incorpora el host Rust. Ambos recorridos usan los mismos argumentos y lock. Cerrar el renderer no cierra el daemon. Salir detiene voz, revoca control y aborta Pi. Reiniciar no repite tareas externas: las tareas que estaban ejecutándose quedan interrumpidas y deben verificarse.

El descriptor del daemon contiene una capacidad local; Windows la protege con DPAPI. En Linux el descriptor solo tiene permisos 0600. Esos permisos no sustituyen aislamiento ante código que ya se ejecuta como el mismo usuario.

OpenAI Realtime y Gemini Live tienen protocolos diferentes. Se confirma la configuración del proveedor antes de enviar audio. Los llamados de voz delegan a la sesión Pi; no exponen todos los MCP al modelo de voz. La transcripción local utiliza Whisper y salida SAPI/Piper por turnos. El detector Vosk recibe audio únicamente cuando se habilita activación local.

Las acciones de escritorio de InputControl/Forge se serializan. El control está deshabilitado hasta que el usuario lo permite desde la interfaz. Detener revoca ese permiso antes de esperar el aborto. Los resultados externos son datos, no nuevas instrucciones. Gmail registra cada intento de envío antes de solicitarlo al proveedor y no repite automáticamente un envío incierto.

Las credenciales se guardan en DPAPI o durante la sesión en memoria. Pi conserva sus mecanismos de /login y proveedores configurados por el usuario. El modo Work bloquea shell y edición de Pi; Code permite sus herramientas cuando se habilita explícitamente en ajustes.

El puente interno rechaza Origin de navegadores y exige token por petición. El gateway opcional tiene su propia contraseña y cookies; no entrega al navegador el token interno ni las claves de los proveedores.
