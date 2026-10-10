"""Build the Windows model pack from pinned upstream files, without user data."""
import argparse
import hashlib
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arise_app.downloads import download_wake, safe_extract

QWEN_REV = 'a615a81362316d7b9f5a7a9c4313adfdf9b54588'
WHISPER_SHA = '9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794'
SOURCES = {
    'models/small.pt': (f'https://openaipublic.azureedge.net/main/whisper/models/{WHISPER_SHA}/small.pt', WHISPER_SHA),
    'models/dialogue.gguf': (f'https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/{QWEN_REV}/qwen2.5-1.5b-instruct-q4_k_m.gguf', '6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e'),
    'llama.zip': ('https://github.com/ggml-org/llama.cpp/releases/download/b10991/llama-b10991-bin-win-cpu-x64.zip', '8f1b7bcc1df032bb0c5759e3db5c67969f20c6f061aa0efec70de7bfa00fbf37'),
}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download(url, path, expected=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and expected and digest(path) == expected:
        return
    temporary = path.with_suffix(path.suffix + '.part')
    print('Downloading ' + path.name, flush=True)
    request = urllib.request.Request(url, headers={'User-Agent':'ARISE-offline-builder'})
    with urllib.request.urlopen(request, timeout=90) as source, temporary.open('wb') as output:
        shutil.copyfileobj(source, output, 1024*1024)
    if expected and digest(temporary) != expected:
        temporary.unlink()
        raise RuntimeError('Checksum mismatch: ' + path.name)
    temporary.replace(path)


def prepare(root, output):
    root, output = Path(root), Path(output)
    root.mkdir(parents=True, exist_ok=True)
    for relative, (url, expected) in SOURCES.items():
        download(url, root/relative, expected)
    safe_extract(root/'llama.zip', root/'server')
    executable = list((root/'server').rglob('llama-server.exe'))
    if len(executable) != 1:
        raise RuntimeError('llama-server.exe missing or ambiguous')
    download_wake(root)
    licenses = {
        'QWEN-LICENSE.txt': f'https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/{QWEN_REV}/LICENSE',
        'WHISPER-LICENSE.txt': 'https://raw.githubusercontent.com/openai/whisper/v20250625/LICENSE',
        'LLAMA-LICENSE.txt': 'https://raw.githubusercontent.com/ggml-org/llama.cpp/b10991/LICENSE',
    }
    for name,url in licenses.items(): download(url,root/'licenses'/name)
    shutil.copy2(Path(__file__).resolve().parents[1]/'arise_app/resources/VOSK-LICENSE.txt',root/'licenses/VOSK-LICENSE.txt')
    files = {p.relative_to(root).as_posix(): digest(p) for directory in ('models','server','licenses') for p in sorted((root/directory).rglob('*')) if p.is_file()}
    manifest = {'format':'arise-offline-pack-v1', 'platform':'windows-x64', 'files':files,
        'server':executable[0].relative_to(root).as_posix(), 'sources':{k:{'url':v[0],'sha256':v[1]} for k,v in SOURCES.items()}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary=output.with_suffix('.tmp')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_STORED, allowZip64=True) as archive:
        archive.writestr('manifest.json',json.dumps(manifest,indent=2))
        for relative in files: archive.write(root/relative,relative)
    temporary.replace(output)
    output.with_suffix('.zip.sha256').write_text(digest(output)+'  '+output.name+'\n')
    print(json.dumps({'path':str(output),'bytes':output.stat().st_size}),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cache',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();prepare(args.cache,args.output)
