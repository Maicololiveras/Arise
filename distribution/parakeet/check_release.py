"""Release gate: never publish an app pointing at missing model assets."""
import json
from pathlib import Path
import sys

manifest = json.loads(Path(__file__).with_name('manifest.json').read_text())
release = json.load(sys.stdin)
assert release.get('isDraft') is False, 'Model release is still a draft'
assets = {asset['name']: asset for asset in release['assets']}
for spec in manifest['files']:
    assert spec['name'] in assets, 'Missing asset: ' + spec['name']
    assert assets[spec['name']]['size'] == spec['size'], 'Wrong size: ' + spec['name']
for name in ('SOURCE.json', 'NOTICE.txt', 'SHA256SUMS'):
    assert name in assets, 'Missing provenance: ' + name
print('Published model and runtime assets are available.')
