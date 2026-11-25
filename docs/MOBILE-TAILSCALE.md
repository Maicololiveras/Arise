# Conectar Arise Mobile a tu red privada

Esta guía corresponde a **Arise Preview 0.4.58** en Windows. El teléfono ejecuta Tailscale y abre la web móvil de Arise en Safari o Chrome. Dentro del escritorio, Arise inicia un proceso propio con la biblioteca oficial tsnet. Aparece como un dispositivo independiente en tu red y solo escucha HTTPS en el puerto 443 de ese nodo. Los mensajes llegan al asistente por tuberías entre procesos. Puedes usar el PC sin instalar el cliente global de Tailscale.

## Canales independientes

| | Preview | Estable (al publicar esta función) |
|---|---|---|
| Nodo y única etiqueta permitida | `arise-preview` · `tag:arise-preview` | `arise-stable` · `tag:arise-stable` |
| Protocolo HTTP privado | `/mobile/preview/v1` | `/mobile/stable/v1` |
| Cookie de sesión | `__Host-arise-preview-v1` | `__Host-arise-stable-v1` |
| Cuenta del autenticador | ARISE Preview | ARISE Estable |

Registra cada nodo con una clave distinta y únicamente la etiqueta de su columna. Configura el autenticador dos veces y genera el QR del chat desde la edición correspondiente. Cada edición tiene su propio estado de Tailscale, secreto TOTP, contador de intentos, invitaciones y registro de dispositivos. Revocar en Preview no revoca en Estable. Si usabas el protocolo anterior, vuelve a vincular los teléfonos. El transporte en ambos canales usa TLS 1.3 sobre Tailscale. Para autorizar Estable añade una regla independiente dirigida a `tag:arise-stable`.

## Preparar la red

1. En el teléfono instala Tailscale, inicia sesión y conecta la VPN. En la consola de administración, abre **Machines**, selecciona ese teléfono y copia su dirección Tailscale IPv4. Activa MFA o passkeys en el proveedor de identidad de tu cuenta.
2. En **DNS** activa **MagicDNS** y los certificados HTTPS. Tailscale solicita un certificado público para el nombre del nodo. Ese nombre puede aparecer en registros públicos de transparencia de certificados. Arise solicita el nombre genérico `arise-preview`.
3. En **Access controls** añade una etiqueta para el nodo y una regla desde el teléfono. Sustituye la IP de ejemplo por la de tu teléfono. Si el teléfono usa la dirección IPv6 de Tailscale, añade también esa dirección individual a los orígenes permitidos. Para una red dedicada este es un ejemplo de política:

```json
{
  "tagOwners": { "tag:arise-preview": ["autogroup:admin"] },
  "hosts": { "movil-arise": "100.101.102.103" },
  "grants": [
    { "src": ["movil-arise"], "dst": ["tag:arise-preview"], "ip": ["tcp:443"] }
  ],
  "tests": [
    { "src": "100.101.102.103", "accept": ["tag:arise-preview:443"], "deny": ["tag:arise-preview:22"] }
  ]
}
```

En una red existente, integra estas entradas en la política vigente y revisa los permisos de otros servicios. Las reglas son aditivas. Una regla general que permita todo el tráfico también concede acceso al nodo. Añade una prueba con la IP real de un segundo dispositivo y `deny: ["tag:arise-preview:443"]` para comprobar el aislamiento antes de guardar. Si ese teléfono ya tiene permiso para otros equipos, restringe por separado esas reglas si quieres limitarlo exclusivamente a Arise.

4. En **Settings → Keys → Generate auth key** genera una clave **de un solo uso**, con vencimiento breve y etiqueta **tag:arise-preview**. Usa un dispositivo persistente para poder reiniciar Arise. Si la red requiere aprobación de dispositivos, aprueba el nodo en **Machines**. Guarda el estado de Arise en tu perfil personal de Windows, fuera de carpetas compartidas o sincronizadas.

## Vincular el chat

1. Abre el chat en Arise para Windows. En **Ajustes → Conexiones → Celular**, configura el autenticador con el primer QR y confirma un código de seis dígitos.
2. Pega la clave de Tailscale en el campo de registro y pulsa **Conectar nodo privado de ARISE**. Arise la entrega al proceso por su entrada privada. En los reinicios utiliza la identidad del nodo guardada en la carpeta de datos de la aplicación. Comprueba el dispositivo etiquetado en **Machines**.
3. Pulsa **Vincular este chat con mi teléfono**. Escanea el segundo QR desde el teléfono con Tailscale conectado. Abre la dirección HTTPS exacta, asigna un nombre al teléfono y usa el siguiente código del autenticador. Arise vincula la sesión al identificador del teléfono verificado por Tailscale. Una copia de la cookie en otro dispositivo queda rechazada. La invitación vale cinco minutos y se consume al vincular.
4. En Android, abre el menú de Chrome y elige **Instalar aplicación**. En iPhone, abre Safari y elige **Compartir → Añadir a pantalla de inicio**. Si el icono instalado pide vinculación, solicita otro QR desde el PC.
5. Abre **Agentes del chat** mientras Gentle ejecuta una tarea con subagentes. Verás nombre, estado y último paso. **Necesita tu atención** lleva a las decisiones pendientes del chat. Revisa la acción y usa un código nuevo para aprobar. El móvil consulta los cambios mientras está abierto.

## Comprobar, migrar y desconectar

- Comprueba que desde el teléfono autorizado abre la URL y que un segundo dispositivo fuera de la regla carece de acceso. Sin emparejar, la URL solo muestra la página de vinculación. Comprueba también que revocar el teléfono desde el escritorio impide leer el chat y decidir solicitudes.
- Si migras desde Serve del PC, revisa `tailscale serve status` en ese equipo. Retira únicamente el manejador anterior de Arise con la CLI de **ese nodo antiguo**. Si era su única publicación HTTPS en 443, usa `tailscale serve --https=443 off` y verifica el estado. Conserva las publicaciones de otros servicios. La versión nueva descarta la configuración de arranque del gateway anterior. Abre el nuevo QR y reemplaza el icono móvil que apunte a la dirección vieja.
- **Detener acceso móvil** apaga el proceso de red y desactiva su arranque automático. **Revocar dispositivo** invalida las credenciales del teléfono para ese chat. Si se pierde el teléfono, revócalo también en Tailscale. Si se copia la carpeta privada del nodo, elimina ese nodo en **Machines** y vuelve a registrarlo con una identidad nueva.
- Si falla la conexión, revisa MagicDNS, HTTPS, el vencimiento de la clave, la etiqueta exacta y la aprobación del dispositivo. Si la página carga pero la aprobación falla, comprueba la hora del teléfono y usa un código TOTP nuevo. El PC debe estar despierto y Arise abierto.
- El cifrado protege el transporte. El PC y el teléfono autorizados pueden ver el contenido del chat. Las herramientas y el proveedor de modelos siguen sujetos a la configuración que hayas elegido en Arise. El nombre del dispositivo y los metadatos necesarios para coordinar la red son visibles para Tailscale.

[tsnet](https://tailscale.com/docs/features/tsnet) · [Certificados HTTPS](https://tailscale.com/kb/1153/enabling-https) · [Política de red](https://tailscale.com/docs/reference/syntax/policy-file)
