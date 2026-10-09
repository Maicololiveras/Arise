# Voz local y modelos

El instalador incluye Vosk small-es-0.42, faster-whisper 1.2.0, OpenAI Whisper 20250625 y PyTorch 2.8.0 CPU. Windows SAPI genera la voz de respuesta. No hace falta una API de voz para el modo local; el agente de texto usa el proveedor configurado en Pi.

**Ajustes > Voz y audio**: proveedor local, motor auto. Auto reutiliza una ruta compatible elegida; sin ella busca faster-whisper en D:\Transcripcion con ia\whisper_models y la caché de Hugging Face, después .pt en %USERPROFILE%\.cache\whisper, y finalmente Vosk integrado. Un .pt nunca se pasa a faster-whisper. También puedes elegir manualmente archivo/carpeta o forzar vosk.

Rutas mostradas por el usuario: base.pt y small.pt en C:\Users\maicolj\.cache\whisper; base, medium y tiny bajo D:\Transcripcion con ia\whisper_models. La captura es referencia: este entorno no puede comprobar ni cargar esos archivos en su PC.

El build produce ARISE-Voice-Models-es.zip (~40 MB), con modelo Vosk, instrucciones, licencia y hashes SHA-256. **Instalar ZIP de modelos de voz** verifica rutas y manifiesto, y copia el modelo a la carpeta de datos. No reemplaza un modelo existente ni instala código del ZIP. No duplica los Whisper que ya tienes. SAPI usa las voces de Windows instaladas; una voz española adicional puede instalarse desde las opciones de idioma de Windows.

La activación por voz es opcional y queda desactivada hasta que la habilites. Las frases deben reconocerse con Vosk: prueba también una frase española, por ejemplo “hola asistente”, si “Arise” no se reconoce con tu pronunciación. El micrófono cerrado en reposo no puede escuchar una frase de activación.

La conversación local es por turnos: transcripción, tarea del agente y voz. No tiene cancelación acústica de eco ni inferencia GPU en el build CPU. Piper sigue disponible si configuras su ejecutable y un modelo ONNX externo; no viene en este ZIP porque Windows ya aporta SAPI.


## Escucha e interrupciones (0.4.0)

La voz local usa STT (Vosk/Whisper), el modelo elegido en Pi/Gentle y TTS (SAPI/Piper). No es un modelo end-to-end speech-to-speech. Puedes usar también un modelo local del agente mediante un proveedor configurado en Pi (por ejemplo tu servidor local compatible).

La captura no espera a que termine una tarea ni a que acabe la salida hablada. VAD delimita frases con unos 500 ms de silencio; STT y delegación se procesan fuera de la captura. Al hablar se interrumpe la salida de voz, y el nuevo texto llega como instrucción/corrección a la sesión actual de Gentle. `deja de hablar` corta solo audio; `cancela la tarea` detiene el trabajo. El historial de Pi y el chat se conserva; la siguiente instrucción puede pedir continuar. Un cambio de chat descarta respuestas habladas tardías de la sesión anterior.

Preguntas select/input/confirm de Gentle se leen y admiten respuesta hablada; una selección admite su número o texto. Aprobaciones de envío Gmail siguen requiriendo revisión visual. El wake word y la voz no abren el chat.

Usa auriculares para evitar capturar el TTS del propio asistente. `Permitir interrupciones en voz local` y el umbral se ajustan en Voz y audio. No hay cancelación acústica de eco ni garantía de latencia fija: depende del micrófono, del tamaño del Whisper, CPU y modelo del agente. La prueba de concurrencia usa audio/TTS simulado; micrófono, calidad y latencia real requieren el PC Windows del usuario.
