# ARISE móvil guiado — QA 0.4.30 / Android 0.2.0

Alcance: Android + Windows. VPS/Coolify se hará en otra versión. Esta entrega es una prueba controlada, no una declaración de ausencia de vulnerabilidades.

## Uso

1. Instala ARISE QA en el PC y comprueba que el chat funciona. Instala Tailscale en ambos equipos e inicia sesión en tu red privada. Activa la verificación fuerte en el proveedor de identidad de Tailscale; ARISE no puede certificar esa configuración por ti.
2. PC: Ajustes > Conexiones, celular y recordatorios > Celular. Configura el autenticador con su QR (o clave manual), y confirma un código. La clave se guarda con DPAPI bajo el usuario de Windows. Conserva acceso al PC como vía de revocación. No compartas ni publiques ese QR.
3. Pulsa Preparar conexión privada automáticamente. El asistente consulta el nombre de Tailscale y configura Serve en localhost. Si falta sesión, autorización de HTTPS o permisos de Windows, atiende el mensaje oficial y repite. No sobrescribe servicios ya existentes ni configura Funnel. Las políticas de acceso de la tailnet siguen siendo responsabilidad de su propietario: limita el acceso al servicio del equipo, no a toda la red.
4. Genera el QR de vinculación de este chat. Android: Abrir Tailscale, Escanear QR del PC y Conectar. El lector requiere Google Play Services; pegar el enlace es la alternativa. La cámara normal también puede abrir el chat privado en el navegador.
5. Confirma la vinculación con el siguiente código del autenticador. La invitación vence en cinco minutos y se consume una sola vez. La sesión dura como máximo 30 días; puede revocarse antes desde el PC o con Desvincular en el móvil.
6. Escribe o pulsa Hablar. Al terminar la grabación, el PC devuelve un borrador: revísalo y pulsa Enviar. La primera solicitud de permiso de micrófono puede requerir pulsar Hablar nuevamente. El modelo local de transcripción debe estar instalado en el PC; se reutiliza el configurado en ARISE, sin abrir su micrófono ni descargar un modelo silenciosamente.
7. Escuchar genera audio en el PC con una voz instalada de Windows. No garantiza Gonzalo si esa voz no está instalada. Las grabaciones entrantes no se escriben a disco; el audio de respuesta utiliza un archivo temporal eliminado al entregar. El texto enviado sí forma parte del historial del chat.
8. Si otro chat está activo, Continuar este chat solicita un cambio explícito y solo lo realiza cuando no hay trabajo/subagentes/terminales activos. Detener nunca cancela trabajos de otro chat. Las aprobaciones de ARISE muestran acción y vista previa; aprobar requiere un código de autenticador nuevo. Las autorizaciones específicas de extensiones de Gentle siguen sus mecanismos existentes.

La configuración mantiene el puerto al reiniciar ARISE y reabre solo localhost. Requiere que ARISE y Tailscale estén activos; no despierta un PC apagado ni omite el inicio de sesión de Windows. Detener acceso móvil deshabilita su restauración; conservar Serve no hace accesible un backend detenido.

## Protecciones y límites comprobables

- Sin API de configuración privilegiada en el servidor móvil. Cada dispositivo está vinculado a un chat.
- Cookies Secure/HttpOnly/SameSite=Strict; validación de Origin en POST; CSP, límites de carga y sin JavaScript bridge nativo privilegiado. La cookie de WebView usa el almacenamiento privado de la app; no se anuncia como clave no exportable de Keystore.
- TOTP de seis dígitos, ventana ±30 s, rechazo de pasos ya usados y bloqueo persistente de cinco minutos tras cinco fallos. Configuración inicial solo en el puente autenticado del PC. Se trata de una segunda verificación de aplicación, no de una passkey ni de una prueba de MFA del proveedor de Tailscale.
- Revocación impide solicitudes posteriores. Una transcripción o síntesis ya iniciada puede terminar consumiendo CPU, pero la autorización se revisa antes de devolver el resultado.
- Cambio de chat y decisiones protegidos por los bloqueos de transición. El cliente nunca puede modificar permisos locales desde el móvil.
- Grabación acotada a 29 segundos, mono PCM16/16 kHz; motor serializado, sin interpretación del audio como código. La voz generada se trata como texto, no XML de SAPI.
- El contenido del chat se renderiza como texto. Imágenes: PNG/JPEG, hasta cuatro, máximo 2 MB cada una. Documentos PDF/Office no están incluidos aún.

## Pendientes antes de distribución general

- Pruebas reales en Android: QR, Tailscale Wi‑Fi/datos, permisos y micrófono, pantalla bloqueada, interrupción por llamada, recuperación de conexión, lectura de respuestas y revocación.
- Validación Windows de Serve, HTTPS, DPAPI, transcripción con el modelo instalado y voz SAPI. CI/Linux y pruebas con dobles no sustituyen esta prueba.
- Firma estable de Android custodiada fuera del repositorio: el pipeline QA sigue usando firma de depuración y una actualización puede requerir reinstalar/revincular. No publicar esto como experiencia de actualización definitiva.
- Passkeys y recuperación de cuenta, notificaciones push, múltiples agentes simultáneos, entrada de documentos y automatización de políticas de red requieren trabajo adicional. La escucha avanzada Porcupine sigue siendo opcional; el flujo principal no requiere claves/modelos móviles.

Referencias: https://tailscale.com/docs/features/tailscale-serve ; https://tailscale.com/docs/multifactor-auth ; https://developers.google.com/ml-kit/vision/barcode-scanning/code-scanner ; https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html
