"""Validate bounded image payloads before forwarding them to Pi."""
import base64

MAX_IMAGES = 4
MAX_IMAGE_BYTES = 2 * 1024 * 1024

def validate_images(images):
    if images is None: return []
    if not isinstance(images, list) or len(images) > MAX_IMAGES:
        raise ValueError('Puedes adjuntar hasta cuatro imágenes.')
    result=[]
    for image in images:
        if not isinstance(image, dict) or image.get('mimeType') not in ('image/png','image/jpeg'):
            raise ValueError('Adjunta una imagen PNG o JPEG.')
        data=image.get('data','')
        if not isinstance(data,str) or len(data)>4*((MAX_IMAGE_BYTES+2)//3):
            raise ValueError('Cada imagen debe ocupar como máximo 2 MB.')
        try: raw=base64.b64decode(data,validate=True)
        except (ValueError,TypeError): raise ValueError('La imagen no contiene datos válidos.') from None
        signature=b'\x89PNG\r\n\x1a\n' if image['mimeType']=='image/png' else b'\xff\xd8\xff'
        if not raw.startswith(signature) or len(raw)>MAX_IMAGE_BYTES:
            raise ValueError('La imagen no coincide con su formato o supera 2 MB.')
        result.append({'type':'image','mimeType':image['mimeType'],'data':data})
    return result


def import_workspace_files(workspace, paths, *, max_bytes=128 * 1024 * 1024):
    """Copy a user-selected batch into a new workspace directory, or leave no copies."""
    import shutil
    import tempfile
    from pathlib import Path

    sources = [Path(p) for p in paths]
    if not 1 <= len(sources) <= 16:
        raise ValueError('Selecciona entre 1 y 16 archivos.')
    root = Path(workspace).resolve(strict=True)
    if any(not p.is_file() for p in sources):
        raise ValueError('Selecciona solo archivos.')
    if sum(p.stat().st_size for p in sources) > max_bytes:
        raise ValueError('Los adjuntos superan 128 MB en total.')
    folder = Path(tempfile.mkdtemp(prefix='adjuntos-', dir=root))
    refs = []
    remaining = max_bytes
    try:
        for src in sources:
            dest = folder / src.name
            n = 2
            while dest.exists():
                dest = folder / f'{src.stem} ({n}){src.suffix}'
                n += 1
            with src.open('rb') as reader, dest.open('xb') as writer:
                while chunk := reader.read(min(1024 * 1024, remaining + 1)):
                    remaining -= len(chunk)
                    if remaining < 0:
                        raise ValueError('Los adjuntos superan 128 MB en total.')
                    writer.write(chunk)
            refs.append(dest.relative_to(root).as_posix())
    except Exception:
        shutil.rmtree(folder)
        raise
    return refs
