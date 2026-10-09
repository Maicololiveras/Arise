# Evidencia de validación

Fecha: 2026-10-09. Plataforma local: Linux, Python 3.12, Qt 6.10.3 offscreen, Node 24, Pi 0.85.1 y Rust 1.90.0.

La suite tiene pruebas de RPC y MCP, Pi real con modelo local simulado, widgets Qt, daemon separado, transporte WebSocket de ambos adaptadores, límites de audio, persistencia, importación de configuración, protección de rutas, adjuntos y confirmación de Gmail, gateway autenticado y extracción segura de modelos.

Los resultados locales completos se encuentran en `docs/local-test-results.json`. `scripts/test.py` produce un nuevo informe en artifacts para cada ejecución y falla si falta el test con Pi real.

Rust: dos pruebas del supervisor pasan; el binario Linux se compiló en release. La compilación Windows se realiza en CI.

Las imágenes de panel/orbe/ajustes se capturaron de los widgets nativos reales, con audio apagado. Son evidencia del renderer y layout en Qt/Linux; no prueban la transparencia de Windows.

Docker en GitHub Actions: PASÓ el 2026-10-09, run [37937629886](https://github.com/Maicololiveras/Arise/actions/runs/37937629886). Se construyó el host Rust (dos pruebas) y se ejecutaron 42 pruebas en el contenedor: cero fallos, errores o skips.

Docker local: NO EJECUTADO. El entorno no tiene Docker y `unshare -Ur` falla con Operation not permitted. No se sustituyó ese resultado por una afirmación de Docker exitoso. La rama incluye un job que ejecuta `docker compose run --build --rm tests` en GitHub Actions.

Windows: el workflow ejecuta pruebas nativas offscreen, compila el host Rust, construye el paquete con sus componentes y comprueba initialize/tools/list de los MCP integrados. Consulta el estado de ese workflow para su resultado; los casos de audio y escritorio interactivo continúan en WINDOWS-CHECK.md.

Cuentas externas: NO UTILIZADAS. No se llamó a un modelo cloud, no se inició OAuth real y no se envió correo. Los adaptadores están implementados; su validación con credenciales reales y dispositivos debe completarse antes de llamar a esta versión una distribución final.

Pendientes de distribución: certificado de firma, actualización firmada, validación en máquina limpia, pruebas de activación/eco y aprobación OAuth pública de Gmail cuando aplique. La configuración VPS/TLS está documentada, no desplegada.

Actualización de proyectos: 45 pruebas locales, incluyendo worktrees reales con cambios sin commit, cierre de procesos, recuperación del chat activo, reanudación del mismo sessionId de Pi y comando /gentle:status sin invocar al modelo.

CI Windows del run 37938061727: pasaron 42 pruebas y dos pruebas de Rust. El empaquetado con herramientas se detuvo al intentar leer repos privados desde Actions. El build base y la opción ARISE_COMPONENTS_TOKEN separan ese requisito de acceso.

Auditoría npm de Pi 0.85.1: tres findings (dos high y uno moderate) en dependencias fijadas por su shrinkwrap, incluidos undici y brace-expansion. Requieren actualizar Pi y revalidar Gentle/protocolo; no se considera esta versión una distribución final endurecida.
