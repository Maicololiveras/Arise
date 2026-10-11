# ARISE 0.4.9 QA

- Comprueba las dependencias de Windows antes de iniciar el asistente de Gentle Shell.
- Reutiliza Node/npm integrados y verifica el tar.exe de Windows.
- Detecta Git con Bash y Go >=1.25.10; instala los ausentes con WinGet y vuelve a verificarlos antes de continuar.
- Prepara pnpm 11.1.1 y npm en una carpeta propia sin reemplazar los gestores globales del usuario.
- Refresca PATH para el proceso del instalador, sin exigir reiniciar ARISE.
- Si falta WinGet, hay una cancelación o un requisito sigue sin funcionar, muestra una acción manual y no inicia Gentle.

Extrae el ZIP completo y ejecuta Configurar ARISE.cmd. Se requiere Internet para preparar dependencias. Windows puede solicitar autorización para instalar Git o Go. La autenticación GitHub y la del proveedor del agente se realizan por separado.
