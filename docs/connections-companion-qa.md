# Conexiones y asistente personal — QA, 22 octubre 2026

Estado: implementación inicial en `qa-connections-companion`, basada en 0.4.23.
No es una release certificada. No se modificó main. Las cuentas externas no se han usado.

## Implementado

- Adaptadores HTTP de salida: Telegram Bot API, WhatsApp Business Cloud API con
  plantilla aprobada de una variable de cuerpo, Outlook Mail.Send y Teams
  ChatMessage.Send. Configurado no equivale a conectado ni a entrega verificada.
- Microsoft OAuth por device authorization, consentimiento explícito,
  renovación y almacenamiento DPAPI por usuario Windows. Client ID propio de
  Entra y clientes públicos habilitados; Teams usa tenant organizations.
- UI en Ajustes > Conexiones, celular y recordatorios, campos con scroll vertical,
  credenciales ocultas y solicitudes de red fuera del hilo de interfaz.
- Recordatorios SQLite por chat: crear/listar/cancelar, fecha ISO con zona,
  repetición por intervalo, confirmación visible, persistencia y recuperación.
  Se conserva una copia en el chat de origen. Los envíos externos tienen el
  destinatario exacto autorizado en la confirmación de creación.
- Ocurrencias reclamadas antes del envío. Un timeout o caída deja entrega
  incierta; nunca reenvía automáticamente. Se conservan los resultados locales.
  No se promete entrega exactamente una vez en una API externa.
- Al reabrir el PC, las repeticiones atrasadas se agrupan en una ocurrencia;
  el siguiente vencimiento conserva la cadencia. No es cron de calendario:
  intervalos de 86400 segundos no representan una hora local fija con DST.
- Puente móvil separado: localhost + Tailscale Serve. Chat vinculado, historial
  de texto, envío y parada. No expone configuración, credenciales ni aprobación
  de permisos. El chat debe estar activo en el PC para enviar o detener.
- Código de vinculación de 192 bits, un uso, cinco minutos. Tokens de dispositivo
  de 256 bits almacenados como SHA-256, cookie Secure/HttpOnly/SameSite=Strict.
  Vigencia de 15 minutos, renovación cada cinco minutos mientras está abierto,
  máximo 30 días, revocación desde el PC. Si expira se vuelve a vincular.
- Borrador móvil conservado ante error, ninguna repetición automática de prompts.
- La delegación existente conserva ID, chat, resultado y aviso al orquestador;
  una salida no cero ya no se presenta como éxito aunque exista result.json.

## Configuración manual para probar

1. Instalar Tailscale y autenticar PC y teléfono en la misma tailnet.
2. Abrir Ajustes > Conexiones > Celular, introducir la URL HTTPS .ts.net del PC.
3. Preparar el servidor y ejecutar el comando `tailscale serve --bg
   http://127.0.0.1:PUERTO` que devuelve ARISE. No usar Funnel. No publicar el
   puerto del puente principal, ni compartir daemon.json.
4. Generar código en el PC y abrir la URL desde el teléfono. El código vincula
   exclusivamente el chat activo. El cierre/reinicio de ARISE detiene el servidor;
   preparar de nuevo y actualizar Serve porque el puerto local puede cambiar.
5. Telegram: crear bot en BotFather y guardar token; el destinatario debe haber
   iniciado contacto. Usar chat ID exacto, no nombre público mutable.
6. WhatsApp: cuenta Business, phone number ID, token válido, versión API admitida,
   plantilla aprobada de una variable e idioma exacto. No sirve una cuenta personal
   vinculada por QR de WhatsApp Web. El titular debe configurar consentimiento.
7. Outlook/Teams: registrar app Entra de cliente público, configurar permisos
   delegados correspondientes, introducir Client ID, autorizar en Microsoft y
   pulsar Comprobar. No usa permisos de aplicación ni impersonación global.
8. Pedir un recordatorio en el chat con fecha/zona y destino explícitos. Revisar
   la confirmación en el PC. La aprobación queda limitada a ese recordatorio.

## Alcance pendiente; no anunciar como disponible

- Mensajería entrante bidireccional de Telegram/WhatsApp/Teams, webhooks con
  validación y deduplicación, asociación segura remitente/chat. Los adaptadores
  de esta iteración solo entregan recordatorios autorizados.
- Outlook lectura/búsqueda/calendario y Teams lectura/canales. No se solicitaron
  scopes de lectura innecesarios para el envío implementado.
- Jobs que ejecuten trabajo del agente, cron con zona/DST, condiciones/eventos,
  límites de concurrencia, resultados de tareas hacia canales externos.
- App Android/iOS y wake word “oye ARISE” en segundo plano. El cliente actual
  es web y solo tiene dictado del teclado del teléfono. No captura audio propio.
- Despliegue automático de Tailscale, alta de dispositivos de red, acceso tras
  reinicio sin configuración, push móvil con la página cerrada, envío de archivos.
- Las tareas existentes permanecen sujetas a Ajustes > Agente > Autorizar ejecución
  local en este chat. El teléfono no habilita ese permiso. Detener mantiene las
  revocaciones de manos/ojos. Cancelar un schedule es una operación independiente.

## Capacidades documentadas de dots y correspondencia

| Capacidad documentada | ARISE / trabajo necesario |
|---|---|
| Conversación mientras se trabaja | Voz/delegación existentes, validar latencias reales |
| Tareas en segundo plano y subagentes | Gentle existente; conservar dueño, eventos y verificación |
| Archivos, análisis, documentos y código | Herramientas locales existentes; verificar cada resultado |
| Recordatorios y recurrencia | Primera versión persistente; falta calendario y jobs de ejecución |
| Seguimiento de eventos de servicios | Pendiente suscripciones/webhooks por proveedor |
| Memoria y notas persistentes | Memoria existente; no compartir conversaciones automáticamente |
| Investigación proactiva de lectura | Pendiente política opt-in y presupuesto |
| Canales ChatGPT/Slack/Teams y llamadas | No transferibles automáticamente; conectores ARISE propios |
| Computador cloud y equipo conectado | ARISE ejecuta en el PC por requisito del usuario |
| Actividad, intervención, pausa y cancelación | Estados existentes; requieren pruebas reales por conector |
| Permisos de apps y límites de divulgación | Consentimiento por conexión y destino, nunca permisos heredados de terceros |

Fuentes oficiales revisadas:
- https://learn.chatgpt.com/docs/dots/tasks-and-memory
- https://learn.chatgpt.com/docs/dots/channels
- https://learn.chatgpt.com/docs/dots/computers-and-apps
- https://core.telegram.org/bots/api
- https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages
- https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-device-code
- https://learn.microsoft.com/en-us/graph/api/user-sendmail?view=graph-rest-1.0
- https://learn.microsoft.com/en-us/graph/api/chat-post-messages?view=graph-rest-1.0
- https://tailscale.com/docs/reference/tailscale-cli/serve
- https://developer.android.com/develop/background-work/services/fgs/service-types

## Voz a voz + suscripción + OAuth

No hay una integración completa comprobada con esas tres condiciones en esta
sesión. No prometer “perfecto” sin comprobar interrupciones, latencia, español,
delegaciones simultáneas, expiración y reconexión.

| Proveedor | Evidencia y límite |
|---|---|
| OpenAI | Sign in with ChatGPT ofrece consumo elegible de Plus/Pro para Responses en apps OSS/locales. No demuestra acceso a GPT-Live/Realtime con ese token. La guía de voz usa project API key. |
| Google | OAuth está documentado para Gemini API. AI Pro/Ultra en AI Studio no cubre el uso directo desde apps externas: facturación API separada. |
| xAI | La API de voz documenta API key o client secret efímero; no se verificó OAuth financiado por suscripción de consumidor. |

Opción a evaluar: STT/TTS locales con orquestador de texto bajo una suscripción
autorizada y Gentle para ejecutar. Es una canalización de voz, no un modelo nativo
voz-a-voz. No cambiar silenciosamente el proveedor ni la voz elegida por el usuario.

- https://developers.openai.com/siwc/token-sharing-open-source
- https://developers.openai.com/api/docs/guides/voice-webrtc
- https://ai.google.dev/gemini-api/docs/google-ai-plans
- https://ai.google.dev/gemini-api/docs/oauth
- https://docs.x.ai/developers/rest-api-reference/inference/voice

## Validación

14 pruebas nuevas: contratos HTTP simulados de proveedores, OAuth pendiente/slowdown/
renovación, plantilla WhatsApp, revocación, caducidad, rotación, vínculo de un uso,
origen HTTP, límites de rutas, cambio de chat, agenda durable, reinicio, cancelación,
agrupación de atrasos y no reenvío ambiguo. No son pruebas contra cuentas reales.
Ventana Qt renderizada en Linux offscreen a 430x640: campos en una columna y scroll
vertical; no equivale a validación de la app instalada en Windows o un teléfono.
Pendiente Windows DPAPI, OAuth real, entregas reales, Tailscale y teléfono físico,
instalador/actualizador, CI Windows y Docker. No publicar release hasta esos gates.

Suite local: 226 pruebas, 220 aprobadas, 6 omitidas por requerir Windows.
Después se añadió y pasó una prueba de salida no cero del delegado (6/6 en esa
suite específica). Los 14 casos nuevos del sistema de conexiones pasaron.
El workflow reconoce esta rama para comprobar Docker/Windows, pero su condición
de publicación sigue limitada a las ramas exactas `qa` y `main`.
