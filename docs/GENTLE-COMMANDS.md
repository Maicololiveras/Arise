# Gentle 4.0.0 en ARISE

El instalador fija gentle-pi/Gentle AI 4.0.0 y Pi 1.1.0. No reemplaza archivos del Gentle instalado: genera adaptadores en caché. Un Pi global anterior a 0.99.1 no sustituye el motor integrado compatible. Los forks o versiones no verificados conservan su código original y pueden tener paneles TUI sin adaptar.

| Comando | Interacción en ARISE |
| --- | --- |
| `/gentle:profiles` | Aplicar, crear, actualizar, duplicar, renombrar, eliminar, exportar/importar y fijar perfil al clon/repositorio. Los handlers originales conservan sus validaciones. |
| `/gentle:models` | Modelo/esfuerzo por agente o todos; guardar/cancelar. No cambia el proveedor de voz. |
| `/gentle:commands` | Paleta de los comandos registrados en la sesión. |
| `/gentle:agents` | Selección de tarea, historial sin thinking y confirmación para detener un agente propio activo. |
| `/gentle:stats` | 7 días, 30 días o todo; alcance proyecto/global; reporte de tokens, costes y sesión. |
| `/gentle:usage` | Consulta real de los proveedores soportados por Gentle; distingue datos disponibles y fallos. |
| `/gentle:changes` | Cambios capturados por Gentle en la sesión; selección de archivo y diff. No atribuye cambios externos. |
| `/gentle:status`, `/gentle:doctor` | Reporte del proyecto y diagnósticos. |
| `/gentle:persona`, `/gentle:vim`, `/gentle:background-subagents` | Diálogos RPC originales y políticas de Gentle. Vim corresponde a su terminal, no al QTextEdit de ARISE. |
| `/gentle:telemetry`, `/gentle:review-mode`, `/gentle:dev-binary`, `/gentle:install-*` | Comandos del handler original; operaciones nativas requieren el helper integrado y condiciones del proyecto. |
| `/history` | Selección de instrucción; la devuelve a la entrada sin enviarla. Captura de historial sigue la política de Gentle. |
| `/gentle:customize` | En la UI de ARISE abre sus ajustes. No simula el panel visual de la terminal ni concede YOLO. |
| Comandos de banner/animación y otros | Se descubren con `get_commands`; mantienen el alcance original de Gentle/TUI. No rediseñan el orbe de ARISE. |

Las preguntas `ask_user_choice` y `ask_user_question` usan el modo RPC interactivo original. Diálogos select, input, confirm y editor aparecen en la ventana nativa. Las notificaciones se guardan en el historial; los comandos desconocidos se rechazan para evitar una llamada accidental al modelo.

Pruebas con Pi/Gentle reales: recuperación del mismo sessionId, crear/aplicar perfil, guardar modelo/esfuerzo, abrir/cerrar paleta/agentes, estadísticas y comandos de diagnóstico sin llamadas adicionales al proveedor de prueba. No se ejecutaron mutaciones de revisión, telemetría o instalación sobre un proyecto real del usuario.
