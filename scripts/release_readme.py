"""Render download links from published channel manifests, never build versions."""
import re

START = '<!-- arise-downloads:start -->'
END = '<!-- arise-downloads:end -->'
REPO = 'https://github.com/Maicololiveras/Arise'


def update_readme(text, manifests):
    if '<!-- arise-windows-stable -->' in text:
        for channel, marker in (('main', 'stable'), ('qa', 'preview')):
            manifest = manifests[channel]
            version = manifest['version']
            tag = ('qa-v' if channel == 'qa' else 'v') + version
            url = f'{REPO}/releases/download/{tag}/ARISE-Setup.exe'
            if not re.fullmatch(r'\d+\.\d+\.\d+', version) or manifest.get('channel') != channel or manifest['installer_url'] != url:
                raise ValueError('Invalid published Windows installer')
            start, end = f'<!-- arise-windows-{marker} -->', f'<!-- /arise-windows-{marker} -->'
            replacement = start + f'[Complete {version}]({url}) · [SHA-256]({url}.sha256)' + end
            text, count = re.subn(re.escape(start) + r'.*?' + re.escape(end), lambda _: replacement, text, flags=re.S)
            if count != 1:
                raise ValueError('Missing or duplicate Windows download cell')
        return text
    rows = []
    for channel, label in (('main', 'Production'), ('qa', 'ARISE Preview')):
        manifest = manifests[channel]
        version = manifest['version']
        if not re.fullmatch(r'\d+\.\d+\.\d+', version):
            raise ValueError('Invalid published version')
        tag = ('qa-v' if channel == 'qa' else 'v') + version
        url = f'{REPO}/releases/download/{tag}/ARISE-Setup.exe'
        if manifest.get('channel') != channel or manifest['installer_url'] != url:
            raise ValueError('Published installer belongs to another channel')
        size = round(manifest['size'] / 1_000_000)
        rows.append(f'- **{label} {version}:** [Windows installer — {size} MB]({url}) · [release and available assets]({REPO}/releases/tag/{tag}).')
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
    """Publish both channel indexes on main; fast-forward the QA mirror safely."""
    import base64
    import json
    if channel not in ('main', 'qa'):
        raise ValueError('Invalid release channel')
    repo = 'repos/Maicololiveras/Arise'
    head = api(f'{repo}/git/ref/heads/main')['object']['sha']
    commit = api(f'{repo}/git/commits/{head}')
    paths = {'main': 'updates/windows.json', 'qa': 'updates/windows-preview.json'}
    manifests = {}
    for name, path in paths.items():
        data = api(f'{repo}/contents/{path}?ref={head}')
        manifests[name] = json.loads(base64.b64decode(data['content']))
    if tuple(map(int, manifest['version'].split('.'))) < tuple(map(int, manifests[channel]['version'].split('.'))):
        raise ValueError('Refusing to replace a newer published version')
    manifests[channel] = manifest
    source = api(f'{repo}/contents/README.md?ref={head}')
    current = base64.b64decode(source['content']).decode('utf-8')
    updated = update_readme(current, manifests)
    entries = [{'path': paths[channel], 'mode': '100644', 'type': 'blob',
                'content': json.dumps(manifest, indent=2) + '\n'}]
    if updated != current:
        entries.append({'path': 'README.md', 'mode': '100644', 'type': 'blob', 'content': updated})
    tree = api(f'{repo}/git/trees', {'base_tree': commit['tree']['sha'], 'tree': entries})
    result = api(f'{repo}/git/commits', {'message': f'Publish {channel} {manifest["version"]} download links [skip ci]',
                                      'parents': [head], 'tree': tree['sha']})
    api(f'{repo}/git/refs/heads/main', {'sha': result['sha'], 'force': False}, method='PATCH')
    if sync_other:
        # Divergent QA work is rejected by GitHub's non-force ref update.
        api(f'{repo}/git/refs/heads/qa', {'sha': result['sha'], 'force': False}, method='PATCH')


def native_downloads(text, version, assets, run_id):
    """Refresh published native links and measured sizes, not stable links."""
    text = re.sub(r'Version \d+\.\d+\.\d+ (?:adds|provides)', 'Version ' + version + ' provides', text)
    text = re.sub(r'native-v\d+\.\d+\.\d+', 'native-v' + version, text)
    text = re.sub(r'ARISE-\d+\.\d+\.\d+-(?=windows|linux|macos)', 'ARISE-' + version + '-', text)
    text = re.sub(r'\[Core \d+\.\d+\.\d+\](?=\([^)]*/native-v)', '[Core ' + version + ']', text)
    text = re.sub(r'Native installers — \d+\.\d+\.\d+ preview', 'ARISE Preview installers — ' + version, text)
    text = re.sub(r'ARISE Preview installers — \d+\.\d+\.\d+', 'ARISE Preview installers — ' + version, text)
    text = text.replace('ARISE Native Preview', 'ARISE Preview')
    text = text.replace('feat/platform-distributions/docs/', 'main/docs/')
    # These two download guides link only the native acceptance run.
    if run_id is not None:
        text = re.sub(r'actions/runs/\d+', 'actions/runs/' + str(run_id), text)
        text = re.sub(r'\[run \d+\]', '[run ' + str(run_id) + ']', text)
    text = re.sub(r'\[\d+\.\d+\.\d+ native prerelease assets\]', '[' + version + ' native prerelease assets]', text)
    for asset in assets:
        if asset['name'].endswith(('.exe', '.deb', '.pkg')):
            pattern = r'(^\|[^\n]*?/native-v' + re.escape(version) + '/' + re.escape(asset['name']) + r'\) \| )\d+ MB'
            text = re.sub(pattern, lambda m: m[1] + str(round(asset['size'] / 1_000_000)) + ' MB', text, flags=re.M)
    return text


def publish_native_metadata(api, version, assets, run_id):
    import base64
    repo = 'repos/Maicololiveras/Arise'
    head = api(f'{repo}/git/ref/heads/main')['object']['sha']
    commit = api(f'{repo}/git/commits/{head}')
    entries = []
    for path in ('README.md', 'docs/NATIVE-DISTRIBUTIONS.md'):
        data = api(f'{repo}/contents/{path}?ref={head}')
        source = base64.b64decode(data['content']).decode('utf-8')
        updated = native_downloads(source, version, assets, run_id)
        if updated != source:
            entries.append({'path': path, 'mode': '100644', 'type': 'blob', 'content': updated})
    if not entries:
        return
    tree = api(f'{repo}/git/trees', {'base_tree': commit['tree']['sha'], 'tree': entries})
    result = api(f'{repo}/git/commits', {'message': f'Publish ARISE Preview {version} native downloads [skip ci]', 'parents': [head], 'tree': tree['sha']})
    for branch in ('main', 'qa'):
        api(f'{repo}/git/refs/heads/{branch}', {'sha': result['sha'], 'force': False}, method='PATCH')
