# Instalar ARISE en otro computador Windows

Necesitas Windows x64, Internet durante la configuración y una cuenta GitHub con acceso a los cuatro repositorios privados de herramientas. La cuenta del proveedor del agente se autentica por separado. La prueba manual de micrófono, escritorio, chat y herramientas en el computador del usuario sigue pendiente; las pruebas automáticas de Windows no la sustituyen.

## Descargar e instalar

- [QA 0.4.8](https://github.com/Maicololiveras/Arise/releases/tag/qa-v0.4.8): pruebas; se actualiza desde `qa`.
- [Producción publicada](https://github.com/Maicololiveras/Arise/releases/latest): se actualiza desde `main`.

Descarga el archivo **ARISE-Windows-Complete.zip** de la publicación, extrae todo y ejecuta **Configurar ARISE.cmd**. El ZIP contiene el instalador y el paquete de modelos. Mantén ambos juntos durante la configuración. Después abre **ARISE** desde Inicio.

El paquete incluye Node, npm, Python, GitHub CLI, FFmpeg y los modelos locales. No necesitas instalar esos runtimes manualmente. Gentle utiliza su asistente oficial y puede descargar sus propios requisitos; elige estable o main explícitamente. Ese selector es independiente del canal QA/producción de ARISE.

## Autenticar GitHub

Tras instalar ARISE en su ruta predeterminada, abre PowerShell como tu usuario habitual y ejecuta:

```powershell
$gh = Join-Path $env:LOCALAPPDATA 'Programs\ARISE\bundle\gh\gh.exe'
& $gh auth login --hostname github.com --git-protocol https --web
& $gh auth status --hostname github.com
```

Si elegiste otra carpeta de instalación, ajusta `$gh`. Completa el código de dispositivo en el navegador con la cuenta que puede leer los repositorios privados. No compartas tokens ni copies credenciales de otro computador.

Comprueba el acceso:

```powershell
foreach ($repo in 'screenview-mcp','inputcontrol-mcp','transcripcion-ia','forge-mcp') {
    & $gh api "repos/Maicololiveras/$repo" --jq .full_name
    if ($LASTEXITCODE -ne 0) { throw "Falta acceso a $repo" }
}
```

También puedes instalar GitHub CLI globalmente, si quieres usar `gh` desde cualquier terminal:

```powershell
winget install --id GitHub.cli --exact --source winget
```

Cierra y abre PowerShell después de esa instalación; usa `gh auth login --hostname github.com --git-protocol https --web` y `gh auth status --hostname github.com`. Es opcional porque ARISE incluye su propio `gh`.

## Completar la configuración

1. Abre ARISE y completa el asistente de Gentle; conserva la elección de canal que prefieras.
2. En Ajustes → Agente, usa **Abrir Pi para /login** y autentica el proveedor. Después pulsa **Conectar y listar modelos** y elige uno disponible.
3. En Ajustes → Herramientas, pulsa **Instalar y reparar dependencias**. ARISE descargará ScreenView, InputControl, Transcripción y Forge con sus dependencias. Después usa **Guardar y comprobar herramientas**.
4. Comprueba que aparecen los cuatro catálogos, envía un mensaje, crea un chat nuevo y prueba micrófono/altavoz. Para voz local elige Vosk/auto y confirma el permiso de micrófono de Windows.
5. Para probar una actualización, conserva tus chats y configuración y acepta la siguiente versión del mismo canal cuando ARISE la ofrezca.

La autenticación GitHub permite descargar las herramientas; no autentica el modelo del agente. Gmail solo requiere configuración si vas a utilizar esa integración.

Referencias: [autenticación de GitHub CLI](https://cli.github.com/manual/gh_auth_login) y [instalación en Windows](https://github.com/cli/cli/blob/trunk/docs/install_windows.md).
