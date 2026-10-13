# ARISE 0.4.10 — instalación con Gentle Shell 4.2

Revisión del 13 de octubre de 2026. Fuente: release oficial v4.2.0 de Gentleman-Programming/gentle-shell y su instalador Windows, SHA-256 `352bf1971c00beb555a97279d59c2ea2946e6b261c446d9b3fe787bd6689a1bb`.

## Cambios incorporados

- Pi integrado 1.2.0 y Gentle Shell 4.2.0, con lockfile actualizado. Node de CI/bundle 24.21.0 y npm 11.19.0.
- El mínimo de Pi se toma del contrato del paquete Gentle instalado. Se rechaza un motor antiguo antes de iniciar RPC.
- Adaptadores RPC de perfiles, modelos, agentes, uso, cambios e historial comprobados con Pi real 1.2.0/Gentle 4.2.0.
- Bootstrap 4.2 sin reescribir ACL ni rutas. Conserva la adquisición verificada de runtimes y la alternativa USERPROFILE cuando AppData no cumple las reglas. El soporte de propietario SYSTEM ya está en upstream.
- ARISE prepara Git/Bash cuando falta. Gentle controla la instalación privada de Node/npm/pnpm/Go y su plan de instalación. Se conserva la confirmación del asistente oficial.
- El reporte reconoce tanto la instalación estándar/main como la distribución privada nueva, con su Node, Pi, versión y carpeta de agente. La sesión recibe el entorno npm del prefijo privado.
- Al terminar el EXE se inicia la configuración de Gentle; con el ZIP completo primero se configuran y prueban los modelos. Piper usa su motor directo y no depende del puente de voz Forge.
- El build audita archivos imprescindibles y compatibilidad Pi/Gentle. `installation-inventory.json` distingue herramientas incluidas y herramientas pendientes de descargar; se incluye como `CONTENIDO-INSTALACION.json` en el ZIP.
- Corregido el cierre de SQLite en la prueba de Ajustes que bloqueó la validación Windows del PR anterior.

## Qué lleva cada entrega

| Componente | Entrega/configuración |
| --- | --- |
| ARISE, supervisor, Node, Pi y Gentle | EXE; rutas configuradas al iniciar |
| Vosk español | EXE; configuración automática |
| Python/pip, FFmpeg/ffprobe, GitHub CLI | EXE |
| Whisper, Qwen y llama.cpp, Piper y voz española | ZIP de modelos completo o descarga individual en Ajustes |
| Git/Bash | Detectados; instalación con WinGet si faltan |
| Entorno del instalador oficial | Adquisición verificada y gestionada por Gentle |
| Forge, ScreenView, InputControl, Transcripción | Incluidos solo si el build tiene acceso a los repositorios privados; el inventario registra el contenido real |
| Proveedores del agente, Gmail y otros servicios personales | Autenticación del usuario; nunca se empaquetan secretos |

## Bloqueos y límites comprobados

Los manifiestos `herramientas/manifests/{forge,screenview,inputcontrol}.json` siguen con `status: pending`. Para descargar sin autenticación deben publicarse los binarios mediante los workflows privados y su secret `TOOLS_PUBLISH_TOKEN`. Para incluir los cuatro MCP dentro del EXE, el workflow de ARISE necesita `ARISE_COMPONENTS_TOKEN`. No se ha afirmado que el paquete base contenga esas herramientas.

La memoria existente no se migra ni se borra. Gentle 4.2 incluye el core Engram 3.4.0, pero un servidor global antiguo debe actualizarse/reiniciarse por su propietario; sus reglas de compatibilidad siguen aplicando. Las credenciales y las decisiones del asistente oficial no pueden completarse en nombre del usuario sin sus datos.

Validación local: suite completa aprobada, incluyendo Pi real con modelo HTTP de prueba (sin cuentas externas), protocolos MCP, comandos/perfiles, modelos y rollback. El reporte del nuevo instalador privado tiene una prueba de integración con fixtures. La descarga y SHA del ZIP oficial y la sintaxis de sus adaptadores fueron comprobados. La instalación final del EXE requiere el gate Windows de GitHub Actions; una prueba local Linux no acredita esa ejecución.
