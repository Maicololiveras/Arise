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


## QA 0.4.17: recuperación del entorno privado

ARISE detecta `%LOCALAPPDATA%\gentle-shell` y `%USERPROFILE%\.gentle-shell-bundle`, o el prefijo adoptado explícitamente. Un launcher --link reconocido conserva prioridad cuando no hay prefijo explícito. Usa prefixLayout, activeVersion y setupEnvironment del helper oficial incluido en el instalador verificado, y la política de binario nativo del paquete instalado. No ejecuta pnpm global para esta recuperación. No copia autenticación ni crea otra carpeta de agente.

La versión debe estar completa (marcador de versión), con Node y paquetes dentro del prefijo. Un entorno incompleto o dos prefijos posibles requieren reparación/selección; no cambian de motor silenciosamente. Configurar Gentle verifica RPC antes de guardar la adopción y restaura ajustes si falla. La detección no inicia Pi ni tareas.

Transcripción declara en la resolución de pip `mcp>=1,<2` dentro del runtime privado, porque su servidor importa `mcp.server.fastmcp`. La comprobación de importación y catálogo posterior sigue siendo obligatoria.

Pruebas: detector ejecutado con Node real y paquetes de fixture, sin Node/pnpm global; verifica rutas privadas, rechazo de integridad nativa e instalación incompleta, ambigüedad. No equivale a una instalación real en Windows. La comprobación de RPC existente conserva cobertura de rollback.

Limitaciones: no se ha identificado el archivo concreto ausente del error entry-storage del PC personal; una instalación que aún no terminó no puede recuperarse. No se omite ese control ni se modifican ACL. El micrófono -9996 falla al abrir el dispositivo y requiere elegir/probar una entrada real; instalar MCP no resuelve por sí solo ese fallo. No hay comprobación física de audio ni de la instalación completa en ese PC.

Validación local final: 190 pruebas, 186 aprobadas y cuatro de junctions Windows omitidas en Linux. MCP 1.30.0 instalado en un venv limpio: importación real de mcp.server.fastmcp correcta; no sustituye la prueba del servidor de transcripción completo en Windows.

### Corrección de la prueba Windows de QA 0.4.17

El run 38720302265 compiló Windows correctamente, pero windows-tests falló en un único caso: el fixture Python escribía el marcador de versión con CRLF en Windows. Gentle lo genera con Node como bytes LF exactos. Se reprodujo el fallo localmente forzando CRLF; el fixture ahora escribe bytes LF y comprueba también el rechazo de CRLF. No se modifica la validación de producción ni se omite ninguna prueba. publish-update conserva su dependencia de todos los jobs: la publicación queda pendiente hasta que el nuevo run apruebe.

El siguiente run 38732037480 superó la detección y falló en la comparación textual de la ruta de Pi: Windows TEMP usaba RUNNER~1 y Path.resolve devolvía runneradmin. El test ahora comprueba identidad de archivo/carpeta con samefile para Node, Pi, Gentle y el home, manteniendo la comprobación del número de argumentos. No cambia rutas ni validaciones de producción.

### Cierre del residente en Docker

El run 38733341391 detectó un fallo independiente al recibir la respuesta de shutdown. El servidor iniciaba shutdown antes de escribir la respuesta HTTP; como sus workers son daemon, el proceso podía salir antes de responder. Ahora detiene las herramientas, escribe y vacía la respuesta y después inicia el cierre del servidor. Si el cliente desconecta durante la respuesta, el cierre se conserva mediante finally. Una prueba fuerza shutdown inmediato para comprobar el orden tanto con cliente conectado como desconectado; se mantiene la prueba con proceso residente real.
