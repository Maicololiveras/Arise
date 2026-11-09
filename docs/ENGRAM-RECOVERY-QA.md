# Recuperación y actualización de Gentle/Engram — QA 0.4.28

Caso observado: MAIX ejecutaba Gentle Shell 4.5.0/Pi 1.4.0 correctamente en RPC desde su lanzador npm, pero ARISE tenía gentle_agent_home vacío. Configurarlo con el home oficial permitió conversar. Engram 3.6.0 estaba instalado en LocalAppData, pero el proveedor dentro de ARISE no encontraba `engram`. Esto no demuestra que todos los PCs tengan la misma causa.

## Acciones en Ajustes > Agente

- Detectar Pi y Gentle Shell: incluye el paquete global npm de Windows y recupera su home mediante el módulo de lanzamiento oficial. Guarda también el prefijo de bundle para no conservar una mezcla de instalaciones. Usa package.json para localizar la entrada real de Pi.
- Actualizar/reinstalar Engram estable: vuelve a consultar https://github.com/Gentleman-Programming/engram/releases/latest, descarga ZIP y checksums de la misma release, verifica SHA-256, extrae únicamente engram.exe a una carpeta nueva propia y ejecuta --version. Solo entonces configura engram_bin y desconecta la sesión Pi para que el próximo arranque reciba ENGRAM_BIN y PATH local al proceso.
- Actualizar Gentle, Pi y Engram: abre el asistente oficial aunque exista una instalación detectada. El usuario revisa su plan y elige estable. Adopta Gentle tras comprobar sus comandos en RPC y después actualiza Engram. No es una transacción única: si falla Engram, la actualización de Gentle puede haber terminado.

No usa --force de npm, no desactiva TLS, no modifica ACL del perfil, no migra ni borra bases de memoria, no finaliza servidores Engram externos. Si hay tareas o subagentes activos, hay que detenerlos antes. ENGRAM_BIN explícito inválido produce error; no se cambia silenciosamente por otro binario.

Engram 3.6.0 era la última release estable al comprobarlo el 28 de octubre de 2026. `gentle-engram` (paquete de integración npm) y `engram.exe` son componentes distintos: no se actualiza indiscriminadamente el paquete de integración fuera de las reglas de Gentle.

Después de actualizar: conectar y listar modelos; pedir mem_doctor y comprobar el proveedor real. Un servidor previo en 127.0.0.1:7437 puede seguir usando otra versión; el actualizador no lo mata ni afirma que haya cambiado. La descarga puede fallar si Windows no confía en el certificado de red: debe corregirse la cadena de confianza, no omitir su validación.

Pendiente independiente: la verificación de InputControl sigue consultando opencode.json. No se soluciona actualizando Engram.
