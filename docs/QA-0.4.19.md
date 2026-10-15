# QA 0.4.19

## Cambios

Actividad plegable a la izquierda, parada compacta a la derecha. Se conserva el título nativo y se elimina la cabecera redundante. Alt+Q recupera el último mensaje del chat sin enviarlo ni sustituir un borrador; también figura en el menú.

`terminal.delegate` solicita confirmación visible, exige ejecución local autorizada y un entorno Gentle configurado. Abre una consola Windows con Node/Pi/Gentle y una sesión propia por tarea. Máximo tres terminales activas. `terminal.list` consulta solo el chat actual; `terminal.cancel` cancela una tarea propia. Cambiar de chat, Detener o cerrar ARISE cancela las terminales administradas. Los resultados se guardan en el chat de origen. No se concede el token de manos/ojos del padre ni se habilita comunicación con sesiones ajenas.

Cada terminal ejecuta un turno de agente (con sus herramientas), devuelve texto público y cierra. Una respuesta del modelo no certifica que el trabajo esté correcto: el padre debe verificarlo. No se recuperan automáticamente procesos después de una caída de ARISE; las tareas quedan interrumpidas y requieren revisión. La carpeta de trabajo no es un aislamiento del sistema de archivos. Se mantienen las restricciones propias de Gentle.

## Instalador Windows

Confirmado: 0.4.18 superó windows-tests pero agotó 600 segundos en la primera instalación, durante la fase de cierre de procesos; publish-update se omitió por ese fallo. El registro no identifica la operación interna bloqueada.

Defecto encontrado: el recorrido de antecesores no detectaba ciclos de PID. Ahora detiene ciclos y padres más recientes que el hijo, limita consultas CIM, ejecuta PowerShell sin interacción y registra etapas en installer-stop.log. La prueba Windows reproduce ciclos y reutilización de PID. No se elimina la comprobación de procesos ni se continúa reemplazando archivos si falla.

## Evidencia y límites

- UI Qt real en Linux a 340×480: actividad y parada caben; el chat gana espacio. Alt+Q probado con Qt.
- Pruebas de aislamiento entre chats, consentimiento, cancelación de proceso real y ausencia del token del puente en el hijo.
- Pi y Gentle reales en PTY Linux con proveedor SSE local controlado: arranque de tarea, respuesta pública, archivo de resultado y salida 0. No equivale a una consola Windows ni a un proveedor externo.
- Pendiente: CI de Windows, instalación sobre ARISE activo, consola visible en Windows, proveedor real y comprobación física del atajo de emergencia. Publicación condicionada a los gates existentes.
