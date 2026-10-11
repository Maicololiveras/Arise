# Windows: completar detección e instalación previa de dependencias en equipos limpios

Destino: https://github.com/Gentleman-Programming/gentle-shell/issues

## Problema

El usuario reporta que, al instalar en otro computador Windows, faltan dependencias y debe prepararlas manualmente. Se solicita detectar los requisitos y ofrecer instalar lo que falte antes de iniciar Gentle Shell.

En main a6c539aced3d68bf673ea48b77302120f1488934, `scripts/installer-preflight.mjs` inventaría Node, pnpm, Pi, Shell, Gentle AI, Go, globalBin y setup. No incluye Git/Git Bash ni tar de Windows. Node/pnpm y Go sí tienen mecanismos de adquisición: este reporte no afirma que toda instalación automática esté ausente.

- Git for Windows/Bash se necesita para las herramientas shell de Pi. GitHub CLI no instala Git ni Bash.
- `scripts/main-channel.mjs` utiliza `System32\tar.exe` para extraer el código de main, pero el requisito no aparece en el inventario previo. Esa descarga utiliza un archivo tar, no git clone.
- Después de instalar un requisito debe releerse PATH y verificarse su ejecutable en el mismo proceso.

Contexto: ARISE 0.4.8, instalador de Gentle Shell v4.0.0, instalación en otro PC Windows. No se adjunta un nuevo log del PC ni se afirma una reproducción completa en VM limpia; se separa el reporte del usuario de las omisiones comprobadas en código.

## Solución manual Windows

Instalar solo lo ausente, desde PowerShell:

```powershell
winget install --id Git.Git --exact --source winget
winget install --id OpenJS.NodeJS.LTS --exact --source winget
winget install --id GoLang.Go --exact --source winget
```

Cerrar y abrir PowerShell. Verificar Node >=24.3.0 para el bootstrap Windows y Go >=1.25.10:

```powershell
git --version
node --version
npm.cmd --version
go version
```

En un equipo limpio sin pnpm:

```powershell
npm.cmd install --global pnpm@11.1.1
pnpm.cmd setup
```

Abrir otra terminal:

```powershell
pnpm.cmd --version
pnpm.cmd bin --global
& "$env:ProgramFiles\Git\bin\bash.exe" --version
& "$env:SystemRoot\System32\tar.exe" --version
```

Ajustar la ruta de Git si corresponde. Sin WinGet, usar los instaladores oficiales de Git, Node y Go. Si falta tar.exe, reparar/actualizar Windows. No reemplazar automáticamente un pnpm global de otro major.

## Resultado esperado

- Inventario visible y completo de requisitos, rutas, versiones y capacidades.
- Instalar lo ausente antes de configurar Gentle Shell, respetando el consentimiento del instalador.
- Reutilizar lo compatible, refrescar PATH y verificar de nuevo después de instalar.
- Si falla una descarga, falta WinGet o se cancela elevación, mostrar comando manual y no declarar el sistema listo.
- Cubrir Windows limpio y PATH antiguo en pruebas, no solo runners que ya incluyen herramientas.

Como mitigación, ARISE agrega una fase previa de requisitos. Referencias: https://git-scm.com/install/windows y https://go.dev/doc/install.
