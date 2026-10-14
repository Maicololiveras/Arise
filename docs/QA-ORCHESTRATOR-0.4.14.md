# QA 0.4.14 — ejecución, continuidad y actividad pública

Solo rama QA. No cambia permisos del sistema, secretos, confirmación de envíos ni main.

## Defectos confirmados en el código

- ARISE añadía una afirmación absoluta de que bash/write/edit estaban bloqueados, incluso con `code_enabled` habilitado. Su extensión bloqueaba esas herramientas con la opción desactivada. No existía herramienta DOCX nativa del catálogo; `files.write` solo escribe texto UTF-8.
- Guardar ajustes no relacionados con Pi cerraba el proceso. Ya existía reutilización del proceso entre mensajes; no se encontró un cierre deliberado por cada respuesta ni al ocultar el panel.
- Los permisos de ejecución se copiaban al crear otro chat. Ahora el chat nuevo empieza sin esa autorización; regresar conserva la elección propia del chat.
- El puente de voz remoto no comprobaba el chat al despachar una llamada tardía. Ahora invalida también al salir y volver al mismo chat.
- Gentle permite subagentes de fondo después de finalizar el turno principal. El `abort` del padre no es una garantía de cancelación de esos trabajos.

No se tuvo acceso al log de la sesión Windows que produjo la copia vacía. Estos hallazgos explican vías reales de fallo, pero no certifican cuál ocurrió en aquel equipo.

## Capacidades y autorización explícita

Ajustes > Agente > **Ver capacidades reales** conecta Pi y muestra catálogo observado, verificación de Gentle, carpeta y autorización de ejecución. Registrar una herramienta no prueba que un proveedor, modelo, dependencia o credencial funcione.

- Archivos: listar, leer y escribir dentro de la carpeta seleccionada.
- Word: `documents.create_docx` y `documents.read_docx`, disponibles sin shell ni escritorio. Python-docx se incluye en el instalador. Creación con título y párrafos no vacíos, reapertura y comparación del contenido, SHA256 y destino. No sobrescribe, no acepta rutas fuera de la carpeta y cancela la publicación tras una parada. Publicación atómica mediante enlace duro (NTFS/POSIX).
- Plantilla: DOCX opcional, conservada y con contenido añadido al final. No se rellenan automáticamente campos, controles o placeholders. No es una reproducción verificada de la plantilla WEG del usuario.
- Shell, write/edit de Pi y ejecución de subagentes: habilitar **Autorizar ejecución local en este chat** y Guardar. El directorio es el punto de inicio, no una sandbox del sistema operativo. Gentle mantiene sus políticas; ARISE no fuerza modos sin confirmación ni modifica sus controles. La opción no activa manos/ojos.
- Subagentes: usa las herramientas reales de Gentle. Si no se observaron en la sesión, se informa como no verificado. No se habilitan por delegación cuando la ejecución está desautorizada. La comunicación con otros orquestadores/chats se bloquea para mantener el aislamiento solicitado.
- Envíos Gmail: siguen requiriendo confirmación visible. No se amplían permisos ni se almacenan secretos en el informe de capacidades.

## Ciclo de vida del chat

Dos mensajes en el mismo chat usan el mismo proceso y sesión. Ocultar el panel, terminar voz o guardar ajustes de voz/apariencia no cierra Pi. Cambiar opciones que determinan el proceso (modelo, ejecutable, autorización) puede reiniciarlo y retomar el mismo archivo de sesión.

Cambiar de chat detiene los trabajos, revoca manos/ojos, guarda checkpoint de mensajes, preferencias y tareas, y cierra el árbol anterior. Los resultados completos y parciales permanecen asociados al chat y su workspace. Al volver se usa `--continue --session` con su archivo; no se repiten acciones ni se reanudan trabajos cancelados automáticamente. Hay cierre explícito en el menú del chat; salir de la aplicación cierra servicios.

La parada conserva Pi si responde al aborto y no hubo delegación. Si hubo subagentes, se cierra conservadoramente el árbol de procesos porque la versión inspeccionada de Gentle no expone un cancel-all RPC directo para ARISE. El siguiente mensaje explícito retoma el historial. Los archivos ya escritos no se deshacen. Resultados externos ambiguos deben verificarse antes de repetir acciones.

## Actividad de ARISE

Cuadro en el flujo del chat, dos líneas plegado; detalle de altura fija, scroll interno y hasta 30 entradas. Actualizarlo no toma foco ni cambia su altura. Confirmaciones y parada siguen visibles.

Fuentes: eventos Pi `tool_execution_start/end`, mensajes de metadatos de modelo y fin de ejecución; bus de Gentle `gentle-pi:notification:source` para estados reales de subagentes. El puente transmite solo identificador y enum de estado, con chat y época de sesión. No transmite prompts, argumentos de shell, resultados completos ni `thinking_delta`. El resumen Word se genera del resultado verificado de la herramienta propia.

Explorando corresponde a herramientas conocidas de lectura/listado; verificando a lectura DOCX; otras herramientas aparecen ejecutando. Sin evento que identifique fase se dice **fase no informada**; no se inventa planificación. Se distingue modelo seleccionado de modelo de respuesta del padre. Modelo de subagentes y total de progreso se indican no informados. Los recuentos son eventos terminados, no porcentaje de trabajo.

Los estados finales, errores, parada y cambio de chat limpian/inactivan la vista. Los eventos tardíos de procesos anteriores se descartan. No se añaden resúmenes automáticos del razonamiento privado.

## Evidencia y límites

Suite local: **175 pruebas aprobadas, sin omisiones**, `python scripts/test.py` (2026-10-14). El smoke del instalador Windows ahora exige crear y releer un DOCX desde el ejecutable empaquetado y conservarlo tras reemplazar la instalación; ese gate queda pendiente de Actions.

- Pruebas con Pi y Gentle reales, proveedor HTTP local determinista: dos mensajes con mismo proceso/sessionId, Word generado por herramienta desde Pi, escritura autorizada, rechazo de delegación sin autorización, subagente real, cambio y retorno conservando sessionId y permisos separados.
- Subagente real en segundo plano: parada cierra el padre y cancela su petición HTTP al modelo. La prueba no usa credenciales de nube.
- Pruebas de DOCX con encabezado de plantilla, lectura de contenido, rechazo de vacíos/sobrescrituras/rutas externas y cancelación antes de publicar.
- Pruebas de actividad: herramientas/subagentes, modelo ausente, error, espera, parada, rechazo de pensamiento privado y eventos de otro chat.
- UI Qt real sobre Linux/offscreen, ventana 340×480, detalle plegado/expandido, foco, tamaño estable, botón de emergencia visible. DOCX de prueba renderizado e inspeccionado; no prueba la plantilla WEG real.
- Pendiente: instalador Windows generado por Actions, prueba física de voz/mouse/atajo, fuentes/DPI de Windows, proveedor de producción y documento E3 con la plantilla WEG real. No se entregó ni investigó aquí el informe E3.

Ampliaciones no implementadas: relleno avanzado de plantillas, visor de resultados por subagente y cancel-all nativo que preserve el padre tras detener trabajos de fondo. Requieren priorización aparte.
