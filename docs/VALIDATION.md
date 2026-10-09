# Evidencia de validación · ARISE 0.3.0

Fecha: 2026-10-09. Linux local, Python 3.12, Qt 6.10.3 offscreen, Node 24, Pi 1.1.0 y Gentle Shell 4.0.0.

50 pruebas locales: cero fallos, errores o skips. Informe completo en local-test-results.json. Incluye Pi/Gentle reales con proveedor HTTP local simulado, sesiones y worktrees, crear/aplicar perfil, guardar modelos/esfuerzo, paleta, agentes, estadísticas, diagnóstico y comandos locales sin consumo adicional del modelo. El teclado nativo verifica Enter, Shift+Enter y altura útil del chat. Las pruebas de voz cloud usan servidores WebSocket locales simulados; las de formatos locales verifican el contrato de cada motor.

El modelo Vosk español oficial se descargó, cargó con Model/KaldiRecognizer reales y procesó PCM de silencio. El ZIP se instaló con su manifiesto SHA-256 y pasó la comprobación de integridad ZIP. No es una prueba de precisión con voz humana. No se accedió a los archivos Whisper de la máquina del usuario; se implementó su detección por las rutas y formatos de su captura.

El helper Gentle AI 4.0.0 Linux se instaló con el instalador oficial y verificación de sus hashes. npm audit sobre las nuevas dependencias fijadas reportó cero vulnerabilidades en esta revisión; no implica ausencia de riesgos desconocidos.

CI: la revisión anterior pasó Docker/Windows en el run 37941203118. La revisión 0.3.0 ejecuta el mismo pipeline, ahora con 50 tests, Vosk incluido, Whisper CPU/.pt y prueba de carga/importación desde el ejecutable congelado. Consulta el run correspondiente al commit actual para sus resultados; no atribuyas la validación anterior al nuevo paquete.

Docker local no ejecutado: este entorno no tiene Docker. Se usa el contenedor real del workflow de GitHub Actions.

Las imágenes panel.png, orb.png y settings.png son capturas de widgets Qt reales en Linux. No prueban transparencia, escalas ni dispositivos en Windows. El smoke Windows comprueba host Rust, daemon congelado, motor Pi/Gentle, renderer Qt, modelo Vosk, importación de Whisper/faster-whisper y disponibilidad de SAPI sin abrir el micrófono.

Los cuatro MCP privados requieren ARISE_COMPONENTS_TOKEN para que Actions los incluya; su catálogo se verifica únicamente en ese build. Sin el secret se entrega la base y se pueden detectar/importar herramientas instaladas.

Cuentas externas no utilizadas. Pendientes en un equipo real: micrófono/altavoz, reconocimiento de la frase elegida, eco e interrupción, calidad/velocidad con los Whisper del usuario, OAuth/Gmail, control de escritorio y funcionamiento en Windows limpio. No hay cancelación acústica de eco ni prueba de voz GPU. Certificado de firma y actualizador firmado no incluidos. VPS/TLS documentado, no desplegado.
