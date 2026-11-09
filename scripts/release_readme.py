"""Render download links from published channel manifests, never build versions."""
import re

START = '<!-- arise-downloads:start -->'
END = '<!-- arise-downloads:end -->'
REPO = 'https://github.com/Maicololiveras/Arise'


def update_readme(text, manifests):
    rows = []
    for channel, label in (('main', 'Producción'), ('qa', 'QA')):
        manifest = manifests[channel]
        version = manifest['version']
        if not re.fullmatch(r'\d+\.\d+\.\d+', version):
            raise ValueError('Invalid published version')
        tag = ('qa-v' if channel == 'qa' else 'v') + version
        url = f'{REPO}/releases/download/{tag}/ARISE-Setup.exe'
        if manifest.get('channel') != channel or manifest['installer_url'] != url:
            raise ValueError('Published installer belongs to another channel')
        size = round(manifest['size'] / 1_000_000)
        rows.append(f'- **{label} {version}:** [instalador Windows — {size} MB]({url}) · [release y archivos disponibles]({REPO}/releases/tag/{tag}).')
    block = START + '\n' + '\n'.join(rows) + '\n' + END
    if START in text and END in text:
        start = text.index(START)
        end = text.index(END, start) + len(END)
        return text[:start] + block + text[end:]
    # Migrate the previous hand-maintained download list once.
    heading = '## Instalar y configurar\n\n'
    start = text.index(heading) + len(heading)
    end = text.index('Para actualizar una instalación existente', start)
    return text[:start] + block + '\n\n' + text[end:]


def publish_metadata(api, channel, manifest, sync_other=True):
    """Atomically update feed + README, then sync the other README.

    Each ref update is a fast-forward against a freshly read head. Concurrent
    commits are preserved; an update conflict fails the job instead of forcing.
    """
    import base64
    import json
    repo = 'repos/Maicololiveras/Arise'
    manifests = {}
    for branch in ('main', 'qa'):
        data = api(f'{repo}/contents/updates/windows.json?ref={branch}')
        manifests[branch] = json.loads(base64.b64decode(data['content']))
    old = tuple(map(int, manifests[channel]['version'].split('.')))
    new = tuple(map(int, manifest['version'].split('.')))
    if new < old:
        raise ValueError('Refusing to replace a newer published version')
    manifests[channel] = manifest
    branches=(channel, 'qa' if channel == 'main' else 'main') if sync_other else (channel,)
    for branch in branches:
        head = api(f'{repo}/git/ref/heads/{branch}')['object']['sha']
        commit = api(f'{repo}/git/commits/{head}')
        source = api(f'{repo}/contents/README.md?ref={head}')
        current = base64.b64decode(source['content']).decode('utf-8')
        updated = update_readme(current, manifests)
        entries = []
        if updated != current:
            entries.append({'path': 'README.md', 'mode': '100644', 'type': 'blob', 'content': updated})
        if branch == channel:
            entries.append({'path': 'updates/windows.json', 'mode': '100644', 'type': 'blob',
                            'content': json.dumps(manifest, indent=2) + '\n'})
        if not entries:
            continue
        tree = api(f'{repo}/git/trees', {'base_tree': commit['tree']['sha'], 'tree': entries})
        result = api(f'{repo}/git/commits', {'message': f'Publish {channel} {manifest["version"]} download links [skip ci]',
                                          'parents': [head], 'tree': tree['sha']})
        api(f'{repo}/git/refs/heads/{branch}', {'sha': result['sha'], 'force': False}, method='PATCH')
