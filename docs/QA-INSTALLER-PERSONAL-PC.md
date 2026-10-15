# QA: instalación en PC personal

## Confirmado

El bootstrap aportado termina con `process-failed (entry-storage)`. En el
instalador oficial 4.2.0 ese paso comprueba el almacenamiento del archivo JS
al que apunta el shim de pnpm existente, antes de iniciar el asistente. El
mensaje no distingue archivo ausente, fallo de PowerShell ni acceso denegado.
No demuestra `acl-mask`. No se cambian permisos ni se omiten validaciones.

El aviso genérico de carga de herramientas proviene del probe de importación
Python, no del cargador de los ejecutables públicos. La instalación automática
agrupaba herramientas públicas y transcripción privada en una transacción;
un fallo de esta última descartaba las descargas públicas anteriores.

## Cambios

- Instalación automática por componente con confirmación de catálogo individual.
- Un fallo no descarta herramientas verificadas ni impide intentar las siguientes.
- La importación de Python emplea diagnóstico acotado y clasificado, con entorno
  sin las credenciales eliminadas durante la instalación; no muestra stderr crudo.
- El error de Gentle identifica entry-storage sin atribuirlo falsamente a ACL.

## Pendiente

- Obtener la ruta y el contenido del shim pnpm en el PC afectado y comprobar
  existencia/permisos del destino, sin ejecutar ni reparar ese destino a ciegas.
- Identificar la excepción concreta de audio; el aviso disponible no la distingue.
- Repetir la instalación real en ese Windows. Pruebas de aislamiento y diagnóstico
  locales no certifican el funcionamiento del instalador en ese equipo.
- No se modifica el override de Gentle AI del usuario ni main.

## Verificación local

178 pruebas pasan en Linux (Qt offscreen), incluidas las regresiones de
aislación de componentes y diagnóstico entry-storage. No equivale a una
instalación verificada en el Windows de rober. Cambios locales, sin publicación.

## Parche 0.4.15

Se confirmó en el PC una junction desde `pnpm/global/v11/<instancia>/node_modules/pnpm`
al almacén `pnpm/store/v11/links/@/pnpm/<versión>/<hash64>/node_modules/pnpm`.
El adaptador del instalador admite exclusivamente esa estructura bajo LOCALAPPDATA.
Valida el archivo solicitado en el destino y todos sus antecesores con las mismas
reglas de propietario/ACL; rechaza otros puntos de redirección, destinos fuera de
ese almacén y rutas ausentes. También conserva la validación de la ruta original.
No modifica permisos, pnpm global, PATH persistente ni main.

Pruebas nativas agregadas para Windows: junction válida y archivo directo,
ACL sin cambios, destino externo, junction encadenada, escritura por Everyone y
destino ausente. Estas pruebas se omiten explícitamente en Linux; requieren CI
Windows antes de considerar validado el parche nativo.

Audio: se separa el fallo de apertura de dispositivos del fallo de modelo; una
carpeta vacía ya no se considera modelo Vosk válido para activación por voz.
La causa del error del usuario no se ha confirmado. No se sustituye Gonzalo.

## Seguimiento 0.4.16

El registro posterior a 0.4.15 sigue indicando process-failed (entry-storage).
La junction quedó cubierta por CI Windows, pero eso no resolvió el fallo real.
Se cambia el transporte del predicado a EncodedCommand y las pruebas nativas
invocan Node -> PowerShell, como producción. Se conservan todas las denegaciones;
se clasifican errores de lectura, ausencia, acceso, longitud, inicio, salida y
tiempo de espera. No se atribuye el error restante a una causa no comprobada.

El aviso de Forge comprobaba el puente antiguo y podía aparecer con Edge
instalado. Se comprueba el adaptador Edge real y se conserva el puente antiguo
cuando existe, sin sustituir voces. Transcripción identifica el módulo Python
que falta. Audio identifica entrada/salida y código numérico de PortAudio;
no se publican excepciones crudas ni se cambian los dispositivos seleccionados.
El error de apertura de dispositivos observado precede a la carga de modelos.
