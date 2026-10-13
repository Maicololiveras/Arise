# Dependencias de Gentle Shell en Windows

ARISE 0.4.9 prepara los requisitos antes de iniciar el asistente oficial. Esta fase reutiliza Node/npm integrados; instala Git for Windows (incluye Bash) y Go con WinGet cuando no encuentra versiones utilizables; prepara pnpm 11.1.1 y npm 11.10.0 en `%USERPROFILE%\ARISE-Gentle-Prerequisites`, con permisos privados verificados. Incluye allí el Node que seleccionan los lanzadores de npm. Si la carpeta ya existe, verifica sus permisos sin modificarlos. Refresca PATH y verifica los ejecutables antes de continuar. No cambia el pnpm global del usuario.

Git/Bash se necesita para el trabajo de Pi. Go >=1.25.10 se prepara para la compilación nativa de Gentle en Windows. El bootstrap oficial Windows exige Node >=24.3.0; ARISE incluye una versión compatible. El extractor `System32\tar.exe` debe existir en Windows. GitHub CLI (`gh`) sirve para autenticación y no sustituye Git ni Bash.

Si no existe WinGet, instala [App Installer](https://learn.microsoft.com/windows/package-manager/winget/) o los instaladores oficiales de [Git](https://git-scm.com/install/windows) y [Go](https://go.dev/doc/install), y reintenta. Si se cancela la autorización de Windows o la instalación falla, ARISE detiene el inicio de Gentle.

## Preparación manual para versiones anteriores o instalación independiente

Ejecuta solamente los comandos correspondientes a dependencias ausentes:

```powershell
winget install --id Git.Git --exact --source winget
winget install --id OpenJS.NodeJS.LTS --exact --source winget
winget install --id GoLang.Go --exact --source winget
```

Abre otra ventana PowerShell para recoger PATH y verifica:

```powershell
git --version
node --version
npm.cmd --version
go version
```

Para un equipo limpio sin pnpm:

```powershell
npm.cmd install --global pnpm@11.1.1
pnpm.cmd setup
```

Abre otra terminal y comprueba:

```powershell
pnpm.cmd --version
pnpm.cmd bin --global
& "$env:ProgramFiles\Git\bin\bash.exe" --version
& "$env:SystemRoot\System32\tar.exe" --version
```

Ajusta la ruta de Git si se instaló en otra carpeta. Si falta el tar de Windows, actualiza o repara el sistema. No sustituyas una versión global de pnpm que otro proyecto necesite; ARISE usa su propia copia.

El canal `main` de Gentle descarga el código como archivo tar; Git no se presenta como requisito de esa descarga. Node/pnpm/Go ya tienen mecanismos de adquisición en el instalador oficial. La mejora solicitada es completar el inventario y la recuperación de requisitos para Windows limpio.
