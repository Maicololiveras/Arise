# ARISE 0.4.16 · QA

- PowerShell: validación de pnpm transportada con EncodedCommand; los errores de E/S se clasifican sin exponer stderr. Las pruebas Windows invocan ahora Node y PowerShell como producción.
- Forge: comprueba el adaptador Edge real; evita el aviso incorrecto basado en el puente antiguo.
- Audio: identifica entrada/salida y código numérico de PortAudio; sin cambiar dispositivos o sustituir la voz.
- Transcripción: identifica el módulo Python ausente, sin mostrar el traceback.
- La causa final en el PC afectado requiere revalidación; no se anuncia resuelta por las pruebas de CI.

# ARISE 0.4.15 · QA

- Gentle: admite la junction local conocida de pnpm v11 y comprueba el destino y sus antecesores; rechaza otros enlaces y permisos de escritura no confiables.
- Instalación automática de herramientas independiente: una transcripción fallida no descarta ScreenView, InputControl ni Forge.
- Audio: distingue errores al abrir dispositivos y modelos Vosk ausentes o incompletos. No cambia la voz ni descarga modelos sin selección.
- Pendiente: prueba en el PC personal afectado. No se ha confirmado la causa de su fallo de audio.

# ARISE 0.4.14 · QA

- Sesión persistente entre mensajes y ajustes de voz; cambio de chat con historial propio y cierre controlado.
- Capacidades reales visibles, autorización local por chat y ejecución mediante Gentle, sin activar escritorio.
- Creación y lectura DOCX sin escritorio, con contenido verificado y plantilla DOCX opcional en modo añadir.
- Actividad de ARISE: cuadro discreto y plegable, estados reales de herramientas/subagentes, modelo cuando se informa y progreso sin porcentajes inventados. No muestra razonamiento privado.
- Parada conserva revocación de manos/ojos; cierra subagentes de fondo sin reiniciarlos automáticamente.

Pruebas locales con Pi/Gentle reales y modelo simulado, DOCX real y UI Qt. Pendiente validación física de Windows, proveedor real y plantilla WEG del usuario. Detalles: docs/QA-ORCHESTRATOR-0.4.14.md.
