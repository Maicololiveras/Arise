"""Reconcile current installation guides with immutable, published GitHub assets."""
import json
import re
import subprocess

try:
    from .release_readme import native_downloads, update_readme
except ImportError:
    from release_readme import native_downloads, update_readme

REPO = 'Maicololiveras/Arise'
START = '<!-- arise-published-platforms:start -->'
END = '<!-- arise-published-platforms:end -->'
GUIDES = ('README.md', 'docs/README.md', 'docs/NATIVE-DISTRIBUTIONS.md',
          'docs/android-companion-qa.md', 'docs/INSTALL-WINDOWS.md',
          'docs/UPDATES.md', 'docs/release-channels.md')


def published_catalog(releases):
    """Select per product, never assume Android and desktop share a version."""
    selected = {}
    for release in releases:
        if release.get('draft') or not release.get('published_at'):
            continue
        tag = release['tag_name']
        match = re.fullmatch(r'(native-v|android-qa-v|qa-v|v)(\d+\.\d+\.\d+)(-qa)?', tag)
        if not match:
            continue
        prefix, version, suffix = match.groups()
        kind = {'native-v': 'native', 'android-qa-v': 'android', 'qa-v': 'preview', 'v': 'stable'}[prefix]
        if suffix and kind != 'android':
            continue
        names = {a['name'] for a in release.get('assets', []) if a.get('size', 0) > 0}
        required = ({f'ARISE-{version}-{os}-{arch}{ext}' for os, ext in
                     (('windows', '-Setup.exe'), ('linux', '.deb'), ('macos', '.pkg'))
                     for arch in ('x64', 'arm64')} if kind == 'native' else
                    {'ARISE-Android-QA.apk'} if kind == 'android' else {'ARISE-Setup.exe'})
        # Incomplete uploads must not become advertised downloads.
        if not required.issubset(names) or not {n + '.sha256' for n in required}.issubset(names):
            continue
        key = tuple(map(int, version.split('.')))
        if kind not in selected or key > selected[kind]['key']:
            selected[kind] = dict(key=key, version=version + (suffix or ''), tag=tag,
                                  assets=release['assets'])
    return selected


def render_catalog(catalog):
    lines = [START, '## Published downloads (automatic)', '',
             'Versions below refer to published installers, not unreleased source changes.', '',
             '| Platform / channel | Published version | Downloads |', '| --- | --- | --- |']
    for kind, label in (('stable', 'Windows complete / stable'), ('preview', 'Windows complete / ARISE Preview'),
                        ('native', 'Windows, Linux and macOS / x64 and ARM64 Preview'), ('android', 'Android / ARISE Preview')):
        item = catalog.get(kind)
        value = f"{item['version']} | [Release and checksums](https://github.com/{REPO}/releases/tag/{item['tag']})" if item else 'Not published | —'
        lines.append(f'| {label} | {value} |')
    lines += ['| iOS | Not published | No iOS installer is currently distributed. |', '', END]
    return '\n'.join(lines)


def replace_block(text, block):
    if START in text:
        if END not in text:
            raise ValueError('Incomplete generated documentation block')
        start = text.index(START)
        end = text.index(END, start) + len(END)
        return text[:start] + block + text[end:]
    first, separator, rest = text.partition('\n')
    return first + '\n\n' + block + '\n' + separator + rest


def api(path, payload=None, method=None):
    args = ['gh', 'api', path]
    if method:
        args += ['--method', method]
    if payload is not None:
        args += ['--input', '-']
    result = subprocess.run(args, input=json.dumps(payload) if payload is not None else None,
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout) if result.stdout.strip() else None


def main():
    import base64
    releases = []
    page = 1
    while True:
        batch = api(f'repos/{REPO}/releases?per_page=100&page={page}')
        releases.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    catalog = published_catalog(releases)
    if not catalog:
        raise RuntimeError('No complete published installers found; refusing to replace documentation')
    root = f'repos/{REPO}'
    head = api(f'{root}/git/ref/heads/main')['object']['sha']
    commit = api(f'{root}/git/commits/{head}')
    block = render_catalog(catalog)
    entries = []
    for path in GUIDES:
        data = api(f'{root}/contents/{path}?ref={head}')
        text = base64.b64decode(data['content']).decode()
        updated = replace_block(text, block)
        if path == 'README.md' and 'stable' in catalog and 'preview' in catalog:
            manifests = {}
            for kind, channel in (('stable', 'main'), ('preview', 'qa')):
                item = catalog[kind]
                asset = next(a for a in item['assets'] if a['name'] == 'ARISE-Setup.exe')
                manifests[channel] = dict(channel=channel, version=item['version'], size=asset['size'],
                    installer_url=f'https://github.com/{REPO}/releases/download/{item["tag"]}/ARISE-Setup.exe')
            updated = update_readme(updated, manifests)
        if path == 'docs/README.md':
            updated = re.sub(r'Native installer \d+\.\d+\.\d+ release notes', 'Native installer release notes', updated)
        if path in ('README.md', 'docs/NATIVE-DISTRIBUTIONS.md') and 'native' in catalog:
            item = catalog['native']
            # Preserve recorded CI evidence: only the publisher knows the acceptance run.
            updated = native_downloads(updated, item['version'], item['assets'], None)
        if updated != text:
            entries.append(dict(path=path, mode='100644', type='blob', content=updated))
    if entries:
        tree = api(f'{root}/git/trees', dict(base_tree=commit['tree']['sha'], tree=entries))
        head = api(f'{root}/git/commits', dict(message='Synchronize published platform documentation [skip ci]',
                    parents=[head], tree=tree['sha']))['sha']
        api(f'{root}/git/refs/heads/main', dict(sha=head, force=False), 'PATCH')
    # Also repair a previous interrupted mirror update; never force divergent QA history.
    api(f'{root}/git/refs/heads/qa', dict(sha=head, force=False), 'PATCH')
    print(f'Documentation reconciled on main and qa: {head}')


if __name__ == '__main__':
    main()
