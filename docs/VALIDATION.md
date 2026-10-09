# Evidencia de validación · ARISE 0.4.0

2026-10-09: 74 pruebas locales aprobadas (sin fallos/errores/skips), 2 pruebas Rust Linux y 2 pruebas Node del renombrado atómico con bloqueos transitorios. Se incluyen clic/doble clic, orbe persistente, seguimiento del panel, guardado de posición, ocultamiento tras un minuto, wake sin abrir chat, SHA/tamaño/origen de actualizaciones desde main, eliminación de Authorization en redirects, cierre de subprocess/descendiente real y conversación local concurrente con correcciones, interrupciones y respuestas a preguntas de Gentle.

El setup de manos/ojos tiene una prueba con repositorios/catálogos simulados; no se descargó su código privado en esta rama pública ni se utilizó una credencial del usuario. El acceso autenticado y el control real de PC necesitan esa cuenta y su equipo. El interlocutor se prueba con un servidor HTTP local simulado, delegación y respuestas mientras Gentle sigue trabajando; STT/TTS se simula y se valida el contrato de motores; no demuestra latencia/eco con un micrófono real.

El workflow valida Docker, Windows, el ejecutable congelado y una reinstalación real sobre UI/daemon/Pi en ejecución. Solo publica el instalador y el descriptor de main si todos esos checks pasan. Consultar el run de 0.4.0 antes de atribuirle el resultado de 0.3.0.

## CI final · ARISE 0.4.0

[Run 37973490621](https://github.com/Maicololiveras/Arise/actions/runs/37973490621): Docker y Windows aprobados, 74 pruebas Python en cada entorno, 2 Rust Linux y 3 Rust Windows, y 2 pruebas Node de reintento del instalador Gentle. El ejecutable congelado pasó host → daemon → Pi/Gentle, memoria, renderer Qt, Vosk, importación de Whisper y voces SAPI.

El instalador pasó instalación limpia y reemplazo real con UI/daemon/Pi en ejecución: cerró 4 procesos hijos propios, conservó chat y memoria, eliminó el archivo obsoleto de _internal y reabrió 0.4.0. Resultado en windows-installer-validation.json. Se validó el commit e062547fa11cf948f84738228ce2a9c2cb274492. El binario se compiló en 3cd85a6c492a42fc8e7cb5915b9046a1e3242cf9 y se reutilizó después de comprobar vía GitHub que solo cambiaron el script de prueba y el workflow; la aplicación y sus entradas de empaquetado eran idénticas. Las pruebas de Windows, del ejecutable congelado y de reinstalación volvieron a ejecutarse.

[Release v0.4.0](https://github.com/Maicololiveras/Arise/releases/tag/v0.4.0) publicada y [main/updates/windows.json](https://github.com/Maicololiveras/Arise/blob/main/updates/windows.json) confirmado. Instalador 388502656 bytes, SHA-256 b0e51a0dede79c031f4e15635d855663ed6d8f97c43bb23e34bad62d57d301f4, coincide con el digest del asset de GitHub. La descarga autenticada y el control de manos/ojos con la cuenta real siguen requiriendo conectar GitHub en el PC; no se usó una credencial del usuario durante estas pruebas.

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
