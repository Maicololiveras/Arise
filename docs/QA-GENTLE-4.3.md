# ARISE 0.4.20 QA · Gentle Shell 4.3.0

Fuente: https://github.com/Gentleman-Programming/gentle-shell/releases/tag/v4.3.0

Paquete npm gentle-pi 4.3.0, Pi 1.2.0 (mínimo declarado >=1.2.0). El instalador oficial Windows se fija al SHA-256 b8d8087fe7ad74e7a2dab9121d09dd9fe5fef3ba6498b59d2fe07f701ae80f36. Se descargó y verificó el ZIP y se aplicaron los adaptadores existentes sin modificar sus contratos ni eliminar comprobaciones ACL.

La release fija Gentle AI 4.2.0, contrato de proveedor 1.4.0 y mantiene capabilities/v2.6. ARISE conserva el instalador nativo oficial, sin editar los hashes o habilitar overrides de desarrollo.

## Integración

- Los adaptadores de paneles nativos aceptan 4.3.0 y conservan sus comprobaciones de estructura; se probaron perfiles/modelos vía RPC real.

- El wrapper resuelve el modo de home mediante el lanzador oficial y solo lo aplica si coincide con el home configurado. Así conserva la configuración aislada nueva; una ruta vinculada o personalizada no se cambia a otro entorno.
- RPC conserva GENTLE_SHELL_INTERACTIVE_HOST=1: las confirmaciones continúan visibles. No se activa YOLO ni se cambian permisos.
- Scratch, TMPDIR de subagentes y registro/limpieza de artefactos pertenecen a Gentle. Los documentos de ARISE siguen guardándose en el workspace del chat.
- La integración sigue descubriendo comandos reales, incluido gentle:scratch; no simula soporte mediante una lista fija.

## Comprobaciones

Pruebas del wrapper contra el módulo real 4.3.0: entorno aislado, vinculado y personalizado; conservación de argumentos RPC y host interactivo. Suite de integración con Pi/Gentle reales y proveedor local controlado: persistencia de sesión, cambio y retorno de chat, subagentes, DOCX, memoria y detención. La prueba RPC comprueba el registro real de gentle:scratch.

Pendiente: CI Windows y prueba del instalador en los PCs afectados. La actualización no demuestra que el error entry-storage esté resuelto. La limpieza de scratch del runtime, todos los comandos TUI y todos los proveedores externos no se certifican con estas pruebas.
