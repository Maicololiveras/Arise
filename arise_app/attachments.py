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

