# Herramientas de ARISE para Windows

Distribución pública de **Forge**, **ScreenView** e **InputControl**. Los repositorios de desarrollo y su historial permanecen privados. Esta rama contiene scripts de distribución y manifiestos; los ejecutables se alojan en Releases de Arise.

## Estado inicial

Los paquetes se publican únicamente después de compilar y verificar el catálogo MCP del ejecutable en Windows. Un manifiesto `pending` significa que esa primera publicación aún no está disponible; el instalador se detiene con un mensaje explícito. No requiere autenticación GitHub del usuario una vez publicados los paquetes.

## Instalar

En Windows x64 con Git instalado:

```powershell
git clone --branch herramientas --single-branch --depth 1 https://github.com/Maicololiveras/Arise.git arise-tools
cd arise-tools
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

Instalar solamente una herramienta:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Tool screenview
```

Se descarga solo lo elegido, se comprueba SHA-256 y se instala por versión en `%LOCALAPPDATA%\Programs\AriseTools`. No necesita instalar Python, Node o Bun. Importa el archivo `mcp.json` generado en tu cliente MCP. No cambia automáticamente ARISE ni la configuración de otros clientes. Vuelve a ejecutar el script para obtener la versión publicada; conserva las versiones anteriores y cierra los clientes antes de retirarlas.

ScreenView incluye captura, ventanas, cambios y OCR nativo de Windows (WinRT), sujeto a los idiomas OCR instalados en el sistema. No descarga EasyOCR ni sus modelos. Forge puede necesitar servicios adicionales según la herramienta invocada (por ejemplo transcripción y el cliente/agente configurado). Esta entrega no incluye Transcripción, modelos de voz ni un LLM.

## Publicación (mantenedor)

Cada repositorio privado usa el workflow `public-tools.yml`, en su rama `distribution/herramientas`. El job construye Windows x64, comprueba `initialize` y `tools/list` sobre el ejecutable, adjunta licencias y sube un artefacto **privado**. El job de publicación solo se ejecuta cuando existe el secreto `TOOLS_PUBLISH_TOKEN`.

1. Crear un token fine-grained limitado a **Maicololiveras/Arise**, con **Contents: Read and write**. No conceder administración ni acceso a los repositorios privados a ese token.
2. Guardarlo como secreto de Actions **TOOLS_PUBLISH_TOKEN** en cada repositorio privado (`forge-mcp`, `screenview-mcp`, `inputcontrol-mcp`). No enviarlo por chat ni incorporarlo a archivos.
3. Ejecutar de nuevo el workflow de la rama `distribution/herramientas` (o incorporar el workflow a la rama de desarrollo para usar `workflow_dispatch`).
4. Confirmar que el job `publish` esté verde y que el manifiesto de la herramienta ya no diga `pending`.

Los tags `herramientas-<tool>-v<version>-<commit>` son exclusivos de herramientas. No cambian los feeds `qa`/`main` de ARISE y no se marcan como última release de la aplicación. Solo se publican ZIP binario y checksum; el archivo fuente del tag automático de GitHub contiene esta rama pública, nunca el repositorio privado.

Los usuarios pueden clonar y abrir propuestas; publicar cambios en el repositorio requiere permisos de escritura. La distribución compilada no es DRM ni impide ingeniería inversa. Se conservan las licencias existentes y las de terceros.
