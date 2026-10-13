# QA de voz, chat y parada — 0.4.13

## Defectos confirmados

- El puente anterior de voz usaba System.Speech; `forge_speak` sí expone `engine=edge`, pero ARISE no seleccionaba ese motor. Había sustitución automática por Windows. Se quitó esa sustitución.
- 25 bloques de 20 ms cerraban un turno local a los 500 ms. Una prueba PCM con una pausa intermedia de 700 ms reproduce dos envíos frente a uno con 1400 ms.
- Estado y privacidad estaban ocultos; un clic en el orbe solo cerraba el chat. Ahora un clic alterna su visibilidad y el estado permanece visible.
- La parada esperaba a Pi, no cerraba ScreenView y la llamada a stop_control podía bloquearse detrás de otra llamada MCP. Se revoca el acceso primero, se cierran procesos propios en paralelo y se rechazan conexiones iniciadas antes de la parada.
- Los selectores recibían la rueda; cerrar Ajustes ocultaba el formulario conservando valores no guardados. Ahora la rueda se ignora y el cierre descarta el formulario.

## Integración de voz

El catálogo real de Forge compilado localmente tiene 22 herramientas y declara `forge_speak` con motores local/edge. El paquete público y la sesión del usuario pueden tener otro catálogo: ARISE verifica el catálogo instalado al iniciar la síntesis.

QA incluye un adaptador del sintetizador msedge-tts usado por Forge, fijado a 2.0.4 y con solicitud/respuesta y cancelación propias. Forge instalado debe exponer Edge; ARISE reproduce el audio por su mezclador cancelable. El adaptador evita interpretar el acuse asíncrono `speaking` del MCP como una reproducción terminada. No instala permisos de escritorio.

En Ajustes, **Usar Gonzalo · Colombia · +5%** selecciona el motor y limpia una selección Piper previa; Guardar aplica los cambios. Windows/Piper siguen siendo opciones explícitas, no sustituciones de Gonzalo.

## Comprobaciones y límites

- Pruebas Python y Node de contrato, errores, pausa natural, conservación del borrador y parada concurrente.
- Interfaz Qt real en Linux con backend offscreen: clic, rueda, cierre/reapertura y capturas a tamaño compacto. Esto no valida audio ni entrada física de Windows.
- Intento de síntesis externa: falló con `Connect Error: {}`. **No se certifica que Gonzalo se haya escuchado**.
- InputControl usa pynput para Ctrl+Alt+Esc. ARISE registra el mismo gesto para su parada general y comunica si el registro falla. La parada de InputControl por sí sola no detiene ScreenView.
- La confirmación de parada corresponde a los procesos MCP que ARISE posee. No afirma cerrar herramientas abiertas fuera de ARISE.
- Un error 503 no dispara reintentos. Recuperar el borrador no lo envía. Ante una respuesta ambigua se pide revisar la tarea; no se promete entrega exactamente una vez.

## Pendiente en Windows

1. Guardar el preset Gonzalo, confirmar Forge conectado y escuchar una frase (+5%). Desconectar Internet y comprobar error visible, sin voz sustitutiva.
2. Dictar una frase con pausas de 700–1000 ms; confirmar un solo mensaje. Probar el umbral con el micrófono real; ruido/ganancia siguen siendo hipótesis.
3. Iniciar control y observación autorizados. Probar botón y Ctrl+Alt+Esc; verificar teclas liberadas, ausencia de acciones/capturas pendientes y que no se reanuden hasta reactivación explícita.
4. Abrir Ajustes a escala 125/150%, usar rueda, cerrar sin guardar y reabrir.

## Propuestas adicionales — no implementadas

1. **Alta:** diagnósticos guiados de micrófono, ruido y voz con reproducción de prueba independiente del agente. Requiere un flujo nuevo.
2. **Alta:** identificadores persistentes de envío y consulta del resultado para resolver cortes de conexión ambiguos sin duplicar tareas. Requiere ampliar el protocolo y el almacenamiento.
3. **Media:** calibración asistida del umbral de voz por dispositivo y perfil de accesibilidad (letra/contraste). Requiere preferencias y pantallas adicionales.

Entrega solo QA. La publicación de QA actualiza su README y feed; no escribe el README de main.
