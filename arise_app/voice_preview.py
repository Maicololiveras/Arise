"""Optional private transcription and conservative Spanish wake-name cleanup."""
import io
import json
import os
import re
import uuid
import wave
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
from .https import tls_context


def clean_name(text):
    return re.sub(r'^(oye|hola|hey)([, ]+)a ra[íi]z(?!\s+de\b)(?=[,!: ]|$)', r'\1\2ARISE', text, flags=re.I)


def transcribe(pcm, model, language):
    # Both credential and destination belong to the server operator. An agent
    # or imported chat preference cannot redirect a bearer token or microphone.
    url=os.environ.get('ARISE_STT_URL','')
    token=os.environ.get('ARISE_STT_TOKEN','')
    parsed=urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or not token:
        raise ValueError('Configura un servidor HTTPS privado y su credencial.')
    buf=io.BytesIO()
    with wave.open(buf,'wb') as wav:
        wav.setparams((1,2,16000,0,'NONE',''));wav.writeframes(pcm)
    boundary=uuid.uuid4().hex
    fields={'model':model}
    if language!='auto':fields['language']=language
    body=b''.join(('--'+boundary+'\r\nContent-Disposition: form-data; name="'+k+'"\r\n\r\n'+v+'\r\n').encode() for k,v in fields.items())
    body+=('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="turn.wav"\r\nContent-Type: audio/wav\r\n\r\n').encode()+buf.getvalue()+('\r\n--'+boundary+'--\r\n').encode()
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self,*args):return None
    req=Request(url,data=body,headers={'Authorization':'Bearer '+token,'Content-Type':'multipart/form-data; boundary='+boundary})
    with build_opener(HTTPSHandler(context=tls_context()),NoRedirect()).open(req,timeout=12) as response:
        data=json.loads(response.read(65537))
    if not isinstance(data,dict) or not isinstance(data.get('text'),str):raise ValueError('Respuesta de transcripción inválida.')
    return data['text'].strip()
