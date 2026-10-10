# Validación en Windows real

Estos casos requieren un Windows con escritorio, micrófono y cuentas de prueba. No quedan demostrados por Docker ni por Qt offscreen.

- [ ] Instalar ARISE-Setup.exe en Windows limpio sin Python/Node previos.
- [ ] Configurar Pi y comprobar que las extensiones de Gentle Shell aparecen en la sesión RPC.
- [ ] Elegir modelo y esfuerzo; mantener autenticaciones existentes de Pi.
- [ ] Probar el microphone/altavoz seleccionado y conversación real de cada proveedor.
- [ ] Decir "Oye Arise" con el modelo Vosk elegido, calibrar pronunciación/frases y medir falsos positivos.
- [ ] Interrumpir salida con auriculares; comprobar que no se realimenta con altavoces. No se ha implementado cancelación acústica de eco.
- [ ] Silenciar y comprobar que el dispositivo de captura se detiene.
- [ ] Probar Ctrl+Alt+A y Ctrl+Alt+Esc sin colisiones con otras aplicaciones.
- [ ] Transparencia, arrastre, varios monitores y escalas 100/150/200%.
- [ ] Cerrar el panel mientras trabaja y reabrirlo sin duplicar la sesión.
- [ ] Conectar los cuatro MCP y comprobar catálogo/versiones reales.
- [ ] Observar Bloc de notas, iniciar control visible, escribir una frase, verificar captura y detener control.
- [ ] Conectar una cuenta Gmail de prueba, buscar y crear borrador con adjunto.
- [ ] Cancelar envío; después autorizar un borrador y verificar que se envió una sola vez.
- [ ] Cortar red durante una acción y verificar el resultado externo antes de repetirla.
- [ ] Reiniciar daemon con tarea activa: queda interrumpida, no se reproduce.
- [ ] Detectar base.pt/small.pt y carpetas base/medium/tiny; elegir cada motor compatible.
- [ ] Probar Enter/Shift+Enter, menú inferior y micrófono del chat ampliado.
- [ ] Crear/aplicar/fijar perfiles con Gentle 4.0.0 y guardar modelos por agente.
- [ ] Probar SAPI/Vosk/Whisper locales y, si se configura, un ejecutable y modelo Piper compatibles.
- [ ] Instalar/desinstalar y verificar arranque opcional con Windows.

La firma Authenticode y un canal de actualizaciones firmado requieren el certificado del distribuidor. Este repositorio no incluye certificados ni presenta builds sin firma como firmados.
