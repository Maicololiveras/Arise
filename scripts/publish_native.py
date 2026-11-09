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
    if __import__('os').environ.get('GITHUB_REF_NAME') != 'main':
        raise RuntimeError('ARISE Preview is published only from main')
    assets = Path(directory)
    tag = f'native-v{__version__}'
    files = []
    for system, extension in [('windows', '-Setup.exe'), ('linux', '.deb'), ('macos', '.pkg')]:
        for arch in ('x64', 'arm64'):
            target = f'{system}-{arch}'
            artifact = assets / f'ARISE-{__version__}-{target}{extension}'
            checksum = Path(str(artifact) + '.sha256')
            expected, name = checksum.read_text().strip().split('  ', 1)
            with artifact.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if name != artifact.name or actual != expected:
                raise RuntimeError(f'Checksum mismatch: {artifact}')
            report_file = assets / f'{target}-installer.json'
            report = json.loads(report_file.read_text())
            if report.get('target') != target or not report.get('profile_preserved'):
                raise RuntimeError(f'Missing preservation evidence: {target}')
            for gate in ('install', 'installed_engine_and_ui', 'same_version_reinstall', 'uninstall'):
                if report.get(gate) != 'passed':
                    raise RuntimeError(f'Missing installer gate: {target}/{gate}')
            files.extend([str(artifact), str(checksum), str(report_file), str(assets / f'{target}-smoke.json')])
    # No --clobber: a published version is immutable; use a new version for fixes.
    repo = 'Maicololiveras/Arise'
    existing = subprocess.run(['gh', 'release', 'view', tag, '--repo', repo], capture_output=True)
    if existing.returncode == 0:
        print('Preview version already published; immutable assets retained. Bump the version for binary changes.')
        return
    subprocess.run(['gh', 'release', 'create', tag, '--repo', repo, '--target', __import__('os').environ['GITHUB_SHA'], '--draft', '--prerelease', '--title', f'ARISE Preview {__version__}', '--notes-file', str(ROOT / 'docs/NATIVE-RELEASE-NOTES.md'), *files], check=True)
    subprocess.run(['gh', 'release', 'edit', tag, '--repo', repo, '--draft=false', '--prerelease', '--latest=false'], check=True)

    from scripts.release_readme import publish_native_metadata
    def api(endpoint, payload=None, method='POST'):
        command = ['gh', 'api', endpoint]
        if payload is not None:
            command += ['--method', method, '--input', '-']
        result = subprocess.run(command, input=json.dumps(payload) if payload is not None else None, check=True, text=True, capture_output=True)
        return json.loads(result.stdout)
    release = api(f'repos/{repo}/releases/tags/{tag}')
    publish_native_metadata(api, __version__, release['assets'], __import__('os').environ['GITHUB_RUN_ID'])


if __name__ == '__main__':
    main(sys.argv[1])
