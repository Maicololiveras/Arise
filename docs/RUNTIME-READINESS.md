# Corrección posterior a 0.4.0: arranque y diagnóstico

El reporte de Windows incluye cierres de Pi, `codegraph: write EPIPE`, fallos
al instalar ScreenView/InputControl y ausencia del interlocutor local. Son
fallos independientes hasta obtener evidencia de su relación. El aviso de
OAuth de Gmail requiere configurar esa integración; no explica un cierre de Pi.

## Cambios

- Pi conserva una cola acotada de stderr en memoria. Solo comunica categorías
  reconocidas y código de salida; nunca envía stderr arbitrario al chat.
- Un fallo de Pi pausa nuevas conexiones durante 30 segundos. Guardar una
  configuración corregida permite probar inmediatamente. No se reproducen tareas.
- Los fallos repetidos de voz se deduplican. El interlocutor se puede recuperar
  después de iniciar el servidor sin tener que reiniciar toda la aplicación.
- El Python embebido instala los backends de compilación declarados por las
  herramientas antes de instalar sus fuentes sin build isolation. Su archivo
  `_pth` no acepta el PYTHONPATH usado por pip para esos entornos aislados.
  Los errores de instalación ya distinguen TLS, dependencias, módulos y conexión.
- El daemon puede iniciar un servidor de inferencia local configurado, esperar
  hasta 60 segundos por un catálogo no vacío y cerrar sus procesos al salir.
  Un servidor externo que ya responde se reutiliza y nunca se termina.

## Configuración del servidor

En **Voz y audio**, configurar la URL compatible con OpenAI, el modelo y
**Arranque del servidor** como lista JSON de ejecutable y argumentos. El comando
debe mantener el servidor en primer plano y configurarlo para escuchar solo en
loopback. No usar un lanzador que deje otro proceso independiente en segundo plano.
Las rutas deben apuntar a un motor y modelo instalados. No introducir credenciales
en los argumentos; la credencial `local-dialogue` se conserva en el almacén existente.

`[]` mantiene el modo servidor externo, por ejemplo LM Studio ya abierto.
Este cambio no descarga modelos ni distribuye un motor de inferencia nuevo. La
respuesta de `/v1/models` confirma el catálogo, no certifica calidad de inferencia
ni soporte de tool calls. El modelo seleccionado debe figurar en ese catálogo.
Si la configuración incluye comando y diálogo local habilitado, el daemon lo
prepara al iniciar; los estados aparecen en `status.model_service`.

## Evaluación del motor existente

Se revisó `praxisgenai-motor-ai-sdk` en su rama predeterminada:

- `python/praxisgenai_sdk/providers/provider_router.py` tiene routing, retry y health.
- `python/praxisgenai_sdk/grpc_server/server.py` crea el servidor, pero su `start`
  no registra implementaciones de servicios de generación. Publicar nombres
  mediante reflection no registra esos servicios.
- ARISE consume HTTP `/v1/models` y `/v1/chat/completions` con tool calls, no gRPC.

Por ello no se conecta ese SDK automáticamente ni se sustituye Pi/Gentle.
Una integración posterior necesita servicios registrados y un adaptador HTTP con
historial/tool calls, más pruebas de inferencia real.

El README actual de `flow-local` (Dictto) indica `openai-whisper` y modelo
`small.pt`; seleccionar ese motor y el archivo .pt en ARISE. Whisper transcribe:
no sustituye al modelo conversacional ni al modelo del agente.

## Límites de validación

Las pruebas de regresión usan procesos reales y un servidor HTTP de prueba;
no reproducen la configuración MCP del PC del usuario ni su micrófono.
No se ha demostrado que codegraph provoque el cierre de Pi. Se mantiene su
configuración; no se desactiva silenciosamente ningún MCP.
Falta probar esta corrección con el instalador Windows y capturar el diagnóstico
del cierre original. Estos cambios aún no son una nueva release.


## Aprovisionamiento automático (0.4.2)

El ZIP completo contiene Pi, Gentle Shell, Node, npm, Python y FFmpeg. Al iniciar, ARISE conserva rutas existentes válidas y configura los componentes integrados para las que faltan, aunque el onboarding ya estuviera completo. No requiere instalación global ni permisos de administrador. Un ZIP incompleto debe extraerse de nuevo: no se simula una instalación correcta.

Al conectar GitHub, ARISE descarga los repositorios privados de ScreenView, InputControl, transcripción y Forge, instala sus dependencias en una carpeta propia nueva y verifica los catálogos MCP. Requiere acceso a esos repositorios y conexión a sus registros de paquetes. Las cuentas de proveedores siguen necesitando autenticación. El marcador installed.json no sustituye la comprobación de rutas.

La prueba Windows del ejecutable empaquetado arranca con onboarding completo y rutas de Pi/Gentle borradas; exige que el motor integrado cargue los comandos reales de Gentle. Las pruebas unitarias cubren detección, reparación, idempotencia y compilación/limpieza de Forge con fixtures; no sustituyen la validación de los repositorios privados en el equipo destino.
