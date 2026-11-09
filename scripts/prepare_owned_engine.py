"""Stage the pinned Engram executable at build time, never on first launch."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arise_app.https import open_https
from arise_app.engram_setup import verified_executable

VERSION = '3.7.0'
NAME = f'engram_{VERSION}_windows_amd64.zip'
SHA256 = '0798d5805e7128c52bd4121bdef0a25c8712b7edf55129fb9f8789c1c0ec2013'
URL = f'https://github.com/Gentleman-Programming/engram/releases/download/v{VERSION}/{NAME}'


def prepare(bundle):
    with open_https(URL, timeout=120) as response:
        data = response.read(64*1024*1024+1)
    if len(data)>64*1024*1024 or hashlib.sha256(data).hexdigest()!=SHA256:
        raise RuntimeError('The bundled Engram archive failed its pinned SHA-256 check.')
    content = verified_executable(data, f'{SHA256}  {NAME}\n'.encode(), NAME)
    directory = Path(bundle)/'engram';directory.mkdir(parents=True, exist_ok=True)
    binary = directory/'engram.exe';binary.write_bytes(content)
    if os.name == 'nt':
        result = subprocess.run([str(binary), '--version'], capture_output=True, text=True, timeout=30)
        if result.returncode or result.stdout.strip() != f'engram {VERSION}':
            raise RuntimeError('The bundled Engram executable did not verify its version.')
    return binary

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--bundle',required=True)
    prepare(parser.parse_args().bundle)
