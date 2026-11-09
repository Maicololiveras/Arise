# Modelos de dictado de ARISE

Rama de distribución: `distribution/parakeet-v3`.
Release fijada: `voice-parakeet-v3-2bda32ec70b0`.

El modelo y los runtimes viven en los assets de esa release, asociados a esta
rama. No se guardan binarios grandes en el historial Git ni se utiliza Git LFS.
Esta rama conserva fuentes, hashes y el flujo reproducible de publicación.

GitHub Actions descarga las versiones originales desde Hugging Face y npm,
verifica los 11 archivos, publica una release preliminar y vuelve a descargar
los archivos publicados para verificar sus hashes antes de hacerla visible.
Una release ya publicada no se sobrescribe. Cualquier cambio de bytes exige
otra versión y nuevos hashes revisados.

El cliente ARISE descarga modelo y motor exclusivamente desde GitHub Releases;
se permite únicamente la redirección HTTPS de assets de GitHub. Un proxy debe
permitir `github.com` y `release-assets.githubusercontent.com`. Esto no corrige
un bloqueo del propio GitHub ni autoriza a desactivar TLS.

Las licencias y atribuciones se incluyen en NOTICE.txt. Los bytes no se
convierten ni se comprimen de nuevo. El modelo ocupa aproximadamente 670 MB;
los 11 assets para todas las plataformas suman 733348427 bytes.
