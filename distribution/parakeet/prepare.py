"""Mirror byte-identical pinned upstream artifacts; no model conversion."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parent


def verify(path, spec):
    digest = hashlib.new(spec['algorithm'])
    size = 0
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            if size > spec['size']: raise ValueError('Artifact exceeds pinned size')
            digest.update(chunk)
    value = digest.hexdigest() if spec['algorithm'] == 'sha256' else 'sha512-' + base64.b64encode(digest.digest()).decode()
    if size != spec['size'] or value != spec['digest']:
        raise ValueError('Artifact does not match original size/digest: ' + spec['name'])


class HTTPSOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.startswith('https://'): raise ValueError('Non-HTTPS redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(destination, spec):
    target = destination / spec['name']
    temporary = target.with_suffix(target.suffix + '.part')
    opener = urllib.request.build_opener(HTTPSOnly())
    for attempt in range(3):
        try:
            request = urllib.request.Request(spec['url'], headers={'User-Agent': 'ARISE-model-mirror/1', 'Accept-Encoding': 'identity'})
            with opener.open(request, timeout=60) as response, temporary.open('wb') as out:
                size = 0
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > spec['size']: raise ValueError('Download exceeds pinned size')
                    out.write(chunk)
            verify(temporary, spec)
            temporary.replace(target)
            print('Verified: ' + spec['name'], flush=True)
            return
        except Exception:
            temporary.unlink(missing_ok=True)
            if attempt == 2: raise
            time.sleep(2 * (attempt + 1))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    args.destination.mkdir(parents=True, exist_ok=True)
    for spec in manifest['files']:
        if args.verify_only: verify(args.destination / spec['name'], spec)
        else: download(args.destination, spec)
    if not args.verify_only:
        (args.destination / 'SOURCE.json').write_text(json.dumps(manifest, indent=2) + '\n')
        (args.destination / 'NOTICE.txt').write_text((ROOT / 'NOTICE.txt').read_text())
        lines = []
        for spec in manifest['files']:
            digest = hashlib.sha256()
            with (args.destination / spec['name']).open('rb') as stream:
                while chunk := stream.read(1024 * 1024): digest.update(chunk)
            lines.append(digest.hexdigest() + '  ' + spec['name'])
        (args.destination / 'SHA256SUMS').write_text('\n'.join(lines) + '\n')
    print('All 11 artifacts verified against original pins.', flush=True)


if __name__ == '__main__': main()
