# ARISE 0.4.8 QA

- La voz usa la misma sesion de Gentle que el chat y sus herramientas habilitadas.
- Voz neuronal local Piper es-MX Ald gestionada por Forge; modelo y motor incluidos en el ZIP.
- Modo CPU ligero automatico para equipos de hasta 10 GB: Vosk, sin cargar Whisper ni mantener el modelo conversacional auxiliar en memoria.
- Reparacion del instalador de Gentle en Windows: carpeta privada con propietario correcto, pnpm PATH y reutilizacion del Pi configurado por Gentle.
- Nuevo chat desde subcarpetas y conservacion de catalogos MCP al guardar ajustes.
- Canal QA separado de main: cada instalacion busca actualizaciones solo en su canal.

Extrae ARISE-Windows-Complete.zip y abre Configurar ARISE.cmd. La primera instalacion de Gentle y los MCP privados requiere Internet y acceso GitHub. El proveedor del agente requiere su configuracion habitual; voz local no significa que el modelo de Gentle sea necesariamente local.
