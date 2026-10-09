# Actualizaciones de ARISE Assistant

La fuente de versiones es **main/updates/windows.json**, consultada mediante la API de GitHub con `ref=main`. La rama de implementación sigue siendo feature/native-orb-daemon. Publicar el descriptor no fusiona el código de la aplicación a main.

El pipeline prueba Docker y Windows, construye el instalador y prueba una reinstalación sobre ARISE en ejecución. Después publica una release inmutable y actualiza el descriptor en main con versión, novedades, asset_id, URL, tamaño y SHA-256. Es necesario incrementar la versión para publicar otro binario. Versiones de tres números, comparadas numéricamente; no se instalan versiones anteriores ni prereleases por accidente.

Al abrir ARISE instalado, la comprobación ocurre en segundo plano. Si hay novedades, muestra **Instalar actualización** / **Más tarde**. La descarga usa la API de assets, también para repos privados, y se verifica antes de ejecutarla. Un launcher PowerShell copiado a una carpeta temporal permanece fuera de los archivos a reemplazar. Pide el cierre del daemon y la UI, espera a guardar la sesión, cierra los procesos hijos propios y ejecuta el instalador en la misma ruta. El instalador también hace ese cierre al ejecutarlo manualmente, incluso para actualizar 0.3.0.

El cierre forzado es solo el último recurso, sobre PID + fecha de creación de procesos de la instalación y sus descendientes; no usa `taskkill /IM node.exe` ni cierra otras terminales. Si no puede cerrarlos, detiene la instalación antes de borrar archivos. Los archivos administrados de _internal y bundle/node se reemplazan; chat, worktrees, configuración, credenciales, memoria y tools en la carpeta de datos se conservan. Al finalizar se vuelve a abrir ARISE.

## GitHub privado

En Credenciales, `github-updates` admite una credencial con lectura de Arise, screenview-mcp e inputcontrol-mcp. Windows la protege con DPAPI. Si existe `gh auth login`, se reutiliza su sesión para github.com. Las credenciales se utilizan en el daemon y no van en el descriptor, URL, launcher, instalador, argumentos de pip ni entorno del agente. Los redirects a los servidores de assets eliminan Authorization.

Al guardar el acceso GitHub, si faltan manos/ojos, el daemon los descarga desde el HEAD de la rama predeterminada de cada repo, fija el SHA descargado, instala sus dependencias en un Python incluido y copia el runtime a la carpeta de datos. No requiere Python del usuario ni privilegios de administrador. Configura los comandos stdio y comprueba los catálogos reales. También hay **Herramientas → Instalar y configurar manos y ojos**. Esta instalación requiere conexión y una cuenta con acceso a los repos privados. Instalar herramientas no activa automáticamente el permiso de control del escritorio.

El SHA-256 detecta descargas incompletas o cambiadas respecto a main; no es una firma Authenticode ni una firma independiente del repositorio. Un error de red no interrumpe el chat. La versión 0.3.0 no tenía actualizador: el primer salto a 0.4.0 se instala manualmente; desde esa versión se usa este flujo.
