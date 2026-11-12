"""Publish six verified installers together; never overwrite an existing release."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from arise_app import __version__


def main(directory):
    assets = Path(directory)
    from arise_app.distribution import native_release
    release_config = native_release()
    stable = release_config['channel'] == 'stable'
    branch = __import__('os').environ.get('GITHUB_REF_NAME')
    if branch != 'weg':
        raise RuntimeError('WEG publication only from weg')
    tag = release_config['tag_prefix'] + __version__
    files = []
    for system, extension in [('windows', '-Setup.exe'), ('linux', '.deb'), ('macos', '.pkg')]:
        for arch in ('x64', 'arm64'):
            target = f'{system}-{arch}'
            artifact = assets / f'ARISE-{__version__}-{target}{extension}'
            checksum = Path(str(artifact) + '.sha256')
            expected, name = checksum.read_text(encoding='utf-8').strip().split('  ', 1)
            with artifact.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if name != artifact.name or actual != expected:
                raise RuntimeError(f'Checksum mismatch: {artifact}')
            report_file = assets / f'{target}-installer.json'
            report = json.loads(report_file.read_text(encoding='utf-8'))
            if stable and (report.get('channel') != 'stable' or report.get('version') != __version__):
                raise RuntimeError(f'Missing stable build evidence: {target}')
            if report.get('target') != target or not report.get('profile_preserved'):
                raise RuntimeError(f'Missing preservation evidence: {target}')
            for gate in ('install', 'installed_engine_and_ui', 'same_version_reinstall', 'uninstall'):
                if report.get(gate) != 'passed':
                    raise RuntimeError(f'Missing installer gate: {target}/{gate}')
            # Preserve build reports while giving published installers WEG names.
            branded = artifact.with_name(artifact.name.replace('ARISE-', 'WEG-', 1))
            __import__('shutil').copyfile(artifact, branded)
            branded_hash = Path(str(branded) + '.sha256')
            branded_hash.write_text(actual + '  ' + branded.name + '\n', encoding='utf-8')
            files.extend([str(branded), str(branded_hash), str(report_file), str(assets / f'{target}-smoke.json')])
    # No --clobber: a published version is immutable; use a new version for fixes.
    repo = 'Maicololiveras/Arise'
    existing = subprocess.run(['gh', 'release', 'view', tag, '--repo', repo], capture_output=True)
    if existing.returncode == 0:
        print('Preview version already published; immutable assets retained. Bump the version for binary changes.')
        return
    notes = ROOT / 'docs/WEG.md'
    if stable:
        notes = assets / 'stable-notes.md'
        notes.write_text(f'# ARISE Core {__version__} — stable\n\nSix native installers built and tested from main. Core does not bundle private desktop MCP tools or offline speech models. Updates are manual. Windows installers are unsigned; macOS packages are ad-hoc signed and not notarized. Physical microphone and desktop control require device acceptance.\n', encoding='utf-8')
    flags = [] if stable else ['--prerelease']
    subprocess.run(['gh', 'release', 'create', tag, '--repo', repo, '--target', __import__('os').environ['GITHUB_SHA'], '--draft', *flags, '--title', f"{release_config['title']} {__version__}", '--notes-file', str(notes), *files], check=True)
    subprocess.run(['gh', 'release', 'edit', tag, '--repo', repo, '--draft=false', '--prerelease=false' if stable else '--prerelease', '--latest=false'], check=True)

    # Intentionally do not update main/qa feeds or ARISE download tables.


if __name__ == '__main__':
    main(sys.argv[1])
