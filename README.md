# ARISE

Un orbe para conversar y trabajar con tu agente en Windows. Identidad ARISE, panel compacto, voz configurable y un proceso residente independiente de la interfaz. Gentle Shell sobre Pi ejecuta las tareas; la interfaz muestra lo que haces, los resultados y las decisiones que requieren tu intervención.

![Panel nativo ARISE](docs/panel.png)

> Implementación inicial en `feature/native-orb-daemon`. Las imágenes se capturaron de los widgets Qt reales en Linux, no de una maqueta web. La validación de micrófono, transparencia, monitores y control de un PC Windows requiere pruebas en ese equipo. Consulta [VALIDATION.md](docs/VALIDATION.md).

## Qué incluye

- Orbe circular de 96 px, arrastrable y configurable entre 48 y 240 px.
- Animación de 24 fotogramas de la esfera ARISE original: atlas PNG de aproximadamente 580 KB, 10 FPS, movimiento reducido y alternativa QPainter.
- Panel de 340 × 500 px, conversación, correcciones de tareas, detener y revisión de acciones.
- Daemon independiente; cerrar el panel no cancela el trabajo. Supervisor de procesos escrito en Rust.
- Detección de Pi, paquetes Gentle Shell instalados y rutas de configuración existentes.
- Conexión mediante RPC de Pi: sesiones, modelos disponibles, esfuerzo, eventos y diálogos de extensiones.
- Voz OpenAI Realtime y Gemini Live con adaptadores independientes, audio nativo y delegación a Gentle Shell.
- Alternativa local: Whisper → Pi → voces Windows SAPI o Piper. Funciona por turnos; no equivale a voz a voz nativa.
- Activación Vosk local configurable, descarga opcional del modelo español, clic y Ctrl+Alt+A.
- Ctrl+Alt+Esc para cancelar tareas y revocar el control.
- MCP stdio, importación de configuraciones, catálogo real y contenido de imagen preservado para modelos con visión.
- Gmail OAuth Desktop con PKCE y DPAPI: buscar, leer, crear borradores con adjuntos y solicitar envío con revisión visible.
- Archivos dentro del workspace y notas explícitas de Memory; las extensiones de memoria existentes de Pi siguen cargándose.
- Modo de código opcional para habilitar las herramientas de shell y edición de Pi.
- Acceso web por texto opcional, con sesión privada, control de origen, CSRF y despliegue detrás de HTTPS.
- Docker, CI de Windows, empaquetado portable y receta de instalador Inno Setup.

## Instalar y configurar

El workflow de Windows genera `dist/ARISE` y, si Inno Setup está disponible, `ARISE-Setup.exe`. El paquete compila la aplicación e incluye Pi/Gentle Shell; con `-WithTools` añade ScreenView, InputControl, Forge y Transcripción. No requiere instalar Python ni Node en la máquina que recibe el paquete.

1. Instala ARISE y abre **Configurar ARISE**.
2. En **Agente**, detecta Pi/Gentle Shell o selecciona las rutas. Si ya tienes proveedores o suscripciones autenticados en Pi, conserva su configuración. Usa **Abrir Pi para /login** para autenticar una cuenta compatible y **Conectar y listar modelos** para elegir el modelo disponible.
3. En **Voz y audio**, elige proveedor, modelo, voz, micrófono y altavoz. En **Credenciales**, guarda la clave del proveedor o úsala únicamente durante esa ejecución.
4. Prueba la conversación. La suscripción del agente y la API de voz son conexiones distintas; elegir un proveedor en la interfaz no concede acceso a sus modelos.
5. Conecta las herramientas y, si deseas activación por voz, descarga/selecciona Vosk, ajusta la frase y activa la escucha local. Desactivada, el micrófono permanece cerrado en reposo.
6. Para Gmail, selecciona un JSON OAuth de Google de tipo Desktop con la API Gmail habilitada y conecta tu cuenta. La distribución pública de ese conector puede requerir verificación por Google.

El programa inicia el daemon automáticamente. Sus menús distinguen **Cerrar panel y orbe** de **Salir de ARISE**, que detiene el motor. La activación y los atajos residen en el daemon. El orbe aparece al abrir la vista; si la vista está cerrada, el daemon puede seguir recibiendo voz y ejecutando tareas.

Para ejecutar desde código en Windows:

```powershell
.\Install-Dev.ps1
.\Start-ARISE.cmd
```

Para compilar:

```powershell
.\scripts\Build-Windows.ps1 -WithTools -ReposRoot C:\Repos -GentlePath C:\Repos\gentle-shell-enterprise
```

`ReposRoot` debe contener `screenview-mcp`, `inputcontrol-mcp`, `transcripcion-ia` y `forge-mcp`. Sin `GentlePath`, el build usa `gentle-pi@3.3.0`; con esa opción puedes empaquetar tu fork. Las credenciales no se incluyen en los paquetes.

## Pruebas

```bash
npm ci --prefix vendor --ignore-scripts
python -m pip install .
QT_QPA_PLATFORM=offscreen python scripts/test.py
cargo test --locked --manifest-path host/Cargo.toml
```

Dentro de Docker:

```bash
docker compose run --build --rm tests
```

La suite utiliza Pi real con un proveedor HTTP local simulado, servidores WebSocket de prueba, procesos MCP de prueba, daemon separado y widgets Qt reales. No utiliza cuentas ni envía correos. El build Windows hace además `initialize` y `tools/list` contra los cuatro MCP empaquetados, sin ejecutar acciones de escritorio.

El entorno de desarrollo original no ofrece Docker y bloquea los namespaces necesarios para un Docker sin privilegios. Por eso el resultado local y el resultado de CI Docker se documentan por separado. Un contenedor Linux no demuestra que funcionen el micrófono o el escritorio de Windows.

## Acceso privado desde navegador / VPS

Consulta [REMOTE.md](docs/REMOTE.md). El gateway ofrece conversación por texto y decisiones; no captura el micrófono del navegador. Un VPS Linux ejecuta herramientas del servidor. Para controlar tu Windows, ejecuta el daemon en ese Windows y conecta mediante una red privada o un proxy TLS. No publiques directamente el puente interno del agente.

## Arquitectura e identidad

[Arquitectura](docs/ARCHITECTURE.md) · [Identidad](assets/identity.json) · [Validación](docs/VALIDATION.md) · [Checklist Windows](docs/WINDOWS-CHECK.md).

Renderer y fuente del orbe reutilizados de [praxisgenai-harness](https://github.com/Maicololiveras/praxisgenai-harness/blob/main/docs/ARISE-ORB.md). JetBrains Mono conserva su licencia OFL. Pi, Gentle Shell y los MCP conservan sus respectivas licencias.
