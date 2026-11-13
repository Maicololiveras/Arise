"""Apply the reviewed, pinned registry backport to build-owned dependencies only."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'vendor/gentle-patches/skill-registry.ts'


def apply(package):
    package = Path(package)
    metadata = json.loads((package / 'package.json').read_text(encoding='utf-8'))
    if metadata.get('name') != 'gentle-pi' or metadata.get('version') != '4.7.0':
        raise RuntimeError('Registry backport requires gentle-pi 4.7.0; review before upgrading')
    source = SOURCE.read_bytes()
    expected = (SOURCE.with_suffix('.sha256')).read_text().strip()
    if hashlib.sha256(source).hexdigest() != expected:
        raise RuntimeError('Registry backport integrity mismatch')
    target = package / 'extensions/skill-registry.ts'
    if target.read_bytes() != source:
        target.write_bytes(source)


if __name__ == '__main__':
    apply(sys.argv[1])
