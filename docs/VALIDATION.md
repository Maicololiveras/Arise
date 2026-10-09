# Evidencia de validación · ARISE 0.4.0

2026-10-09: 68 pruebas locales aprobadas (sin fallos/errores/skips), y 2 pruebas Rust Linux. Se incluyen clic/doble clic, orbe persistente, seguimiento del panel, guardado de posición, ocultamiento tras un minuto, wake sin abrir chat, SHA/tamaño/origen de actualizaciones desde main, eliminación de Authorization en redirects, cierre de subprocess/descendiente real y conversación local concurrente con correcciones, interrupciones y respuestas a preguntas de Gentle.

El setup de manos/ojos tiene una prueba con repositorios/catálogos simulados; no se descargó su código privado en esta rama pública ni se utilizó una credencial del usuario. El acceso autenticado y el control real de PC necesitan esa cuenta y su equipo. La nueva voz local se prueba con STT/TTS simulado y el contrato de motores; no demuestra latencia/eco con un micrófono real.

El workflow valida Docker, Windows, el ejecutable congelado y una reinstalación real sobre UI/daemon/Pi en ejecución. Solo publica el instalador y el descriptor de main si todos esos checks pasan. Consultar el run de 0.4.0 antes de atribuirle el resultado de 0.3.0.

## Evidencia previa · ARISE 0.3.0

Fecha: 2026-10-09. Linux local, Python 3.12, Qt 6.10.3 offscreen, Node 24, Pi 1.1.0 y Gentle Shell 4.0.0.

51 pruebas locales: cero fallos, errores o skips. Informe completo en local-test-results.json. Incluye Pi/Gentle reales con proveedor HTTP local simulado, sesiones y worktrees, crear/aplicar perfil, guardar modelos/esfuerzo, paleta, agentes, estadísticas, diagnóstico y comandos locales sin consumo adicional del modelo. El teclado nativo verifica Enter, Shift+Enter y altura útil del chat. El editor RPC devuelve texto multilínea y los diálogos del chat anterior se cierran al cambiar de sesión. Las pruebas de voz cloud usan servidores WebSocket locales simulados; las de formatos locales verifican el contrato de cada motor.

El modelo Vosk español oficial se descargó, cargó con Model/KaldiRecognizer reales y procesó PCM de silencio. El ZIP se instaló con su manifiesto SHA-256 y pasó la comprobación de integridad ZIP. No es una prueba de precisión con voz humana. No se accedió a los archivos Whisper de la máquina del usuario; se implementó su detección por las rutas y formatos de su captura.

El helper Gentle AI 4.0.0 Linux se instaló con el instalador oficial y verificación de sus hashes. npm audit sobre las nuevas dependencias fijadas reportó cero vulnerabilidades en esta revisión; no implica ausencia de riesgos desconocidos.

CI 0.3.0: [run 37954993176](https://github.com/Maicololiveras/Arise/actions/runs/37954993176), commit e9ebdb308269fe8434b1e6a2f60a2ff5b17ec791. Docker y Windows completados correctamente: 51 pruebas Python en cada entorno y 2 del supervisor Rust en Windows. Se generó ARISE-Setup.exe y pasó la prueba del host Rust → daemon congelado → Pi/Gentle, memoria y renderer Qt. Desde el ejecutable se cargó Vosk, se importaron faster-whisper y OpenAI Whisper y se detectaron 2 voces SAPI; no se abrió el micrófono. [Descargar artefacto Windows](https://github.com/Maicololiveras/Arise/actions/runs/37954993176/artifacts/11628570722) (incluye instalador, portable y resultados). Los commits posteriores de README/GIF/documentación no cambian el código probado.

Docker local no ejecutado: este entorno no tiene Docker. Se usa el contenedor real del workflow de GitHub Actions.

Las imágenes panel.png, orb.png y settings.png son capturas de widgets Qt reales en Linux. No prueban transparencia, escalas ni dispositivos en Windows. El smoke Windows comprueba host Rust, daemon congelado, motor Pi/Gentle, renderer Qt, modelo Vosk, importación de Whisper/faster-whisper y disponibilidad de SAPI sin abrir el micrófono.

Los cuatro MCP privados requieren ARISE_COMPONENTS_TOKEN para que Actions los incluya; su catálogo se verifica únicamente en ese build. Sin el secret se entrega la base y se pueden detectar/importar herramientas instaladas.

Cuentas externas no utilizadas. Pendientes en un equipo real: micrófono/altavoz, reconocimiento de la frase elegida, eco e interrupción, calidad/velocidad con los Whisper del usuario, OAuth/Gmail, control de escritorio y funcionamiento en Windows limpio. No hay cancelación acústica de eco ni prueba de voz GPU. Certificado de firma y actualizador firmado no incluidos. VPS/TLS documentado, no desplegado.
