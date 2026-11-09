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
        match = re.fullmatch(r'(native-stable-v|native-v|android-qa-v|android-v|qa-v|v)(\d+\.\d+\.\d+)(-qa)?', tag)
        if not match:
            continue
        prefix, version, suffix = match.groups()
        kind = {'native-v': 'native', 'android-qa-v': 'android', 'qa-v': 'preview', 'v': 'stable', 'native-stable-v': 'native_stable', 'android-v': 'android_stable'}[prefix]
        if kind in ('stable', 'native_stable', 'android_stable') and release.get('prerelease'):
            continue
        if suffix and kind != 'android':
            continue
        names = {a['name'] for a in release.get('assets', []) if a.get('size', 0) > 0}
        required = ({f'ARISE-{version}-{os}-{arch}{ext}' for os, ext in
                     (('windows', '-Setup.exe'), ('linux', '.deb'), ('macos', '.pkg'))
                     for arch in ('x64', 'arm64')} if kind in ('native', 'native_stable') else
                    {'ARISE-Android-QA.apk'} if kind == 'android' else {'ARISE-Android.apk', 'ARISE-Android.aab'} if kind == 'android_stable' else {'ARISE-Setup.exe'})
        # Incomplete uploads must not become advertised downloads.
        if not required.issubset(names) or not {n + '.sha256' for n in required}.issubset(names):
            continue
        key = tuple(map(int, version.split('.')))
        if kind not in selected or key > selected[kind]['key']:
            selected[kind] = dict(key=key, version=version + (suffix or ''), tag=tag,
                                  assets=release['assets'])
    return selected


def render_catalog(catalog, readme_url=""):
    def link(kind, filename, label=""):
        item = catalog.get(kind)
        if not item:
            return "Not released"
        url = f"https://github.com/{REPO}/releases/download/{item['tag']}/{filename}"
        return f"[{label + ' ' if label else ''}{item['version']}]({url}) · [SHA-256]({url}.sha256)"

    def native(os, arch, kind="native"):
        item = catalog.get(kind)
        if not item:
            return "Not released"
        ext = {'windows': '-Setup.exe', 'linux': '.deb', 'macos': '.pkg'}[os]
        return link(kind, f"ARISE-{item['version']}-{os}-{arch}{ext}", 'Core')

    def instructions(system):
        return f"[Install →]({readme_url}#install-{system})"

    stable = '<!-- arise-windows-stable -->' + link('stable', 'ARISE-Setup.exe', 'Complete') + '<!-- /arise-windows-stable -->'
    preview = '<!-- arise-windows-preview -->' + link('preview', 'ARISE-Setup.exe', 'Complete') + '<!-- /arise-windows-preview -->'
    def mobile(channel, system):
        kinds = ('stable', 'native_stable') if channel == 'stable' else ('preview', 'native')
        hosts = [catalog[k] for k in kinds if k in catalog and catalog[k]['key'] >= (0, 4, 41)]
        if not hosts:
            return 'Web app requires PC 0.4.41+ (pending publication)'
        host = max(hosts, key=lambda item: item['key'])
        return f"[Web app · PC {host['version']}]({readme_url}#install-{system})"

    rows = [
        ('Windows 11', 'x64', stable + '<br>' + native('windows', 'x64', 'native_stable'), preview + '<br>' + native('windows', 'x64'), 'windows'),
        ('Windows 11', 'ARM64', native('windows', 'arm64', 'native_stable'), native('windows', 'arm64'), 'windows'),
        ('Linux · Ubuntu 24.04', 'x64', native('linux', 'x64', 'native_stable'), native('linux', 'x64'), 'linux'),
        ('Linux · Ubuntu 24.04', 'ARM64', native('linux', 'arm64', 'native_stable'), native('linux', 'arm64'), 'linux'),
        ('macOS 15', 'Intel x64', native('macos', 'x64', 'native_stable'), native('macos', 'x64'), 'macos'),
        ('macOS 15', 'Apple Silicon ARM64', native('macos', 'arm64', 'native_stable'), native('macos', 'arm64'), 'macos'),
        ('Android', 'Installable web app', mobile('stable', 'android'), mobile('preview', 'android'), 'android'),
        ('iOS / iPadOS', 'Installable web app', mobile('stable', 'ios'), mobile('preview', 'ios'), 'ios'),
    ]
    lines = [START, '## Downloads', '',
        'Choose your system and channel. Desktop downloads point to published installers. Mobile web apps are served by your own updated PC; their links open installation instructions.', '',
        '| Operating system | Architecture | Stable | ARISE Preview | Installation |',
        '| --- | --- | --- | --- | --- |']
    lines += [f'| {os} | {arch} | {stable} | {preview} | {instructions(system)} |'
              for os, arch, stable, preview, system in rows]
    lines += ['', '**Stable** is the established release channel. **ARISE Preview** is for testing newer builds. Stable Core packages retain the same documented capability limits as Core Preview.', '',
        '**Complete** and **Core** are different packages: Core packages include the integrated agent engine, but exclude private desktop MCP servers and offline speech models. A higher Core version does not imply feature parity with Complete.', '',
        '“Not released” means no installer is currently published for that platform and channel. Mobile PWA installation requires no app-store developer account or signing key; native mobile releases are deferred.', '', END]
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
    for branch in ('main', 'qa'):
        head = api(f'{root}/git/ref/heads/{branch}')['object']['sha']
        commit = api(f'{root}/git/commits/{head}')
        entries = []
        for path in GUIDES:
            data = api(f'{root}/contents/{path}?ref={head}')
            text = base64.b64decode(data['content']).decode()
            block = render_catalog(catalog, "" if path == "README.md" else f"https://github.com/{REPO}/blob/main/README.md")
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
            api(f'{root}/git/refs/heads/{branch}', dict(sha=head, force=False), 'PATCH')
    print('Documentation reconciled independently on main and qa')



if __name__ == '__main__':
    main()
