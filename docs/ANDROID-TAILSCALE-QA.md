# Flujo guiado desde Windows 0.4.30 / Android 0.2.0

Para las versiones nuevas sigue [MOBILE-GUIDED-QA.md](MOBILE-GUIDED-QA.md): autenticador, preparación automática y QR. Las instrucciones de abajo describen el flujo manual anterior.

# Android Companion QA: conexión y actualizaciones

## Estado y límites

Android 0.1.1-qa reutiliza el primer fotograma de assets/orb-atlas.png, el mismo origen que arise_app.brand. El icono pequeño de notificación es una silueta separada por las reglas del sistema Android.
Consulta metadatos públicos de versiones al abrir la pantalla de configuración y mediante el botón Buscar actualización / ver descarga. La consulta no envía tokens de vinculación. Un fallo de red no bloquea el chat. El APK se abre en el navegador tras confirmación; Android autoriza su instalación.

Los APK actuales se firman para depuración en CI. No hay una clave estable de distribución configurada: Android puede rechazar una actualización sobre el APK anterior por cambio de firma. No se promete conservar configuración mediante reinstalación. La clave estable debe custodiarse fuera del repositorio; ninguna clave privada ni contraseña se incluye en estos cambios. La firma estable tampoco garantiza que Google retire un aviso de Play Protect.

## PC y teléfono

1. Primero comprueba que el chat de ARISE funciona en el PC. Un error de Pi con salida 1 debe resolverse por separado: Tailscale no lo corrige.
2. Instala Tailscale desde https://tailscale.com/download en Windows y desde la tienda oficial en Android. Conecta ambos a la misma cuenta/red Tailscale. No necesitas exit node ni Funnel.
3. En PowerShell del PC:

```powershell
tailscale status
$estado = tailscale status --json | ConvertFrom-Json
$url = 'https://' + $estado.Self.DNSName.TrimEnd('.')
$url
```

Si no encuentra el comando, abre otra terminal tras instalar Tailscale. El nombre debe terminar en .ts.net.

4. En ARISE, abre el chat que quieres usar. Ajustes > Conexiones, celular y recordatorios > Celular. Pega la URL HTTPS anterior, sin barra final ni puerto, y pulsa Preparar servidor privado.
5. Copia el comando `tailscale serve --bg http://127.0.0.1:PUERTO` que devuelve ARISE. Ejecuta ese comando en PowerShell como administrador. No inventes el puerto ni uses el puerto del puente principal de escritorio. Si Tailscale indica que hay que habilitar HTTPS/Serve, sigue su enlace y después repite el comando.
6. Comprueba `tailscale serve status`. Debe mostrar la URL privada .ts.net y el destino localhost indicado por ARISE. Si ya usabas Serve para otro servicio, revisa esa configuración antes de sustituirla.
7. En el teléfono, activa Tailscale. Abre ARISE Companion, introduce la misma URL y pulsa Guardar conexión y vincular chat.
8. En el PC pulsa Generar código para este chat (5 minutos). Introduce ese código en el panel del teléfono y pulsa Vincular. No publiques el código.
9. Envía un mensaje corto desde el teléfono. Comprueba que llega al chat correcto del PC y que la respuesta regresa al móvil. El chat de origen debe seguir activo en el PC; permisos de ejecución local y control de escritorio se autorizan allí.

Para iPad: Tailscale + Safari con la misma URL. El APK, la burbuja y el detector Android no funcionan en iPad.

## Voz opcional

El chat manual no necesita permiso de micrófono ni superposición. Para la burbuja y activación por voz, permite superposición, micrófono y notificaciones desde los botones de la aplicación. Configura tu AccessKey de Picovoice, el modelo .ppn de «oye ARISE» para Android y el modelo español .pv compatible, y pulsa Activar escucha. No se suministran clave ni modelo personalizado. Apagar micrófono y quitar burbuja detiene la escucha; ocultar el panel no la detiene.

## Reinicio y revocación

El PC debe permanecer encendido y ARISE abierto. Tras reiniciar ARISE prepara de nuevo el servidor privado: su puerto puede cambiar y tendrás que actualizar Serve. Si la sesión móvil expira, genera otro código. Desde el PC puedes revocar el dispositivo o detener acceso móvil. Esto no cancela automáticamente recordatorios ya autorizados.

Referencias oficiales: https://tailscale.com/docs/features/tailscale-serve y https://tailscale.com/docs/reference/examples/serve.
