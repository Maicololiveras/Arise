"""Build a native, relocatable core preview on the target OS and CPU."""
import argparse
import hashlib
import io
import json
import os
import plistlib
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arise_app import __version__
from arise_app.platforms import target
from arise_app.https import open_https

HASHES = {
    'macos-x64': 'd35623443a5d85e8f78338cda5d0bb73b2f7ec6217a57e4abb71904a3e0d6287',
    'macos-arm64': 'f96e08db8f47ca49ebc034eba30e468db81eb56df98f9bf21a73366b510695e4',
    'linux-x64': '8db9d5db1c1574b8b830aac4ffbe86c024014aed6b9a3f0406ac3361a152cdf0',
    'linux-arm64': 'cdbbcb68d3e842d3e52e27edccef55e6fe98ce3cdbc90cd79894323b029efb50',
    'windows-x64': '515a716ce966202058d4b9f310626fde72583cfc64ccefbf0dcc81456260089c',
    'windows-arm64': '01e4f5dab2f941cf810d1373e7c6998c014499bee9c2d5783e34da94c70ac7f2',
}
ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def public_bundle_permissions(package):
    """Allow users to read system-installed code, never profile data or symlinks.

    The official native installer creates a private 0700/0600 download cache.
    This tree contains only distributable code and public integrity manifests.
    Normalize it before sealing the macOS app or building root-owned packages.
    """
    for path in [package, *package.rglob('*')]:
        if path.is_symlink():
            continue
        if path.is_dir():
            path.chmod(0o755)
        elif path.is_file():
            path.chmod(0o755 if path.stat().st_mode & 0o111 else 0o644)


def stage_engram(bundle, identity):
    system, arch = identity.split('-')
    upstream = {'macos': 'darwin'}.get(system, system)
    cpu = {'x64': 'amd64'}.get(arch, arch)
    extension = 'zip' if system == 'windows' else 'tar.gz'
    name = f'engram_3.7.2_{upstream}_{cpu}.{extension}'
    url = f'https://github.com/Gentleman-Programming/engram/releases/download/v3.7.2/{name}'
    with open_https(url, timeout=120) as response:
        data = response.read(64 * 1024**2 + 1)
    if len(data) > 64 * 1024**2 or hashlib.sha256(data).hexdigest() != HASHES[identity]:
        raise RuntimeError('Engram failed its pinned SHA-256 verification')
    executable = 'engram.exe' if system == 'windows' else 'engram'
    # Read only the expected regular member; never extract paths or symlinks.
    if extension == 'zip':
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            matches = [m for m in archive.infolist() if m.filename == executable and not m.is_dir()]
            if len(matches) != 1 or matches[0].file_size > 128 * 1024**2:
                raise RuntimeError('Invalid Engram archive')
            content = archive.read(matches[0])
    else:
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            matches = [m for m in archive.getmembers() if m.name == executable and m.isfile()]
            if len(matches) != 1 or matches[0].size > 128 * 1024**2:
                raise RuntimeError('Invalid Engram archive')
            content = archive.extractfile(matches[0]).read()
    directory = bundle / 'engram'; directory.mkdir()
    binary = directory / executable; binary.write_bytes(content); binary.chmod(0o755)
    result = run(binary, '--version', capture_output=True, text=True)
    if result.stdout.strip() != 'engram 3.7.2':
        raise RuntimeError('Engram version mismatch')


def build(expected):
    identity = target()
    if identity != expected:
        raise RuntimeError(f'Native runner mismatch: expected {expected}, got {identity}')
    windows = os.name == 'nt'; mac = sys.platform == 'darwin'
    suffix = '.exe' if windows else ''
    node = shutil.which('node'); npm = shutil.which('npm.cmd' if windows else 'npm')
    report = json.loads(run(node, '-p', 'JSON.stringify({arch:process.arch,version:process.version})', capture_output=True, text=True).stdout)
    if report != {'arch': identity.split('-')[1], 'version': 'v24.21.0'}:
        raise RuntimeError(f'Unexpected Node runtime: {report}')
    rust = run('rustc', '-vV', capture_output=True, text=True).stdout
    cpu = 'aarch64' if identity.endswith('arm64') else 'x86_64'
    if not any(line.startswith('host: ' + cpu + '-') for line in rust.splitlines()):
        raise RuntimeError('Rust compiler host does not match the native target')
    from arise_app.distribution import native_release
    release = native_release()
    marker = ROOT / 'arise_app/resources/update-channel.json'
    marker.write_text(json.dumps({'channel': release['build_channel'], 'target': identity, 'format': 'native-core'}))
    run('cargo', 'build', '--release', '--locked', '--manifest-path', ROOT / 'host/Cargo.toml')
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed', '--onedir', '--name', 'ARISE',
               '--collect-all', 'truststore', '--collect-all', 'docx', '--collect-all', 'sounddevice', '--collect-all', 'miniaudio']
    if identity not in ('windows-arm64', 'macos-x64', 'macos-arm64'):
        command += ['--collect-all', 'vosk']
    for name in ('web', 'assets', 'arise_app/resources'):
        command += ['--add-data', name + os.pathsep + name]
    run(*command, 'run.py')
    package = ROOT / ('dist/ARISE.app' if mac else 'dist/ARISE')
    application = package / 'Contents/Resources' if mac else package
    shutil.copy2(ROOT / ('host/target/release/arise-host' + suffix), application / ('ARISE-host' + suffix))
    bundle = application / 'bundle'; bundle.mkdir()
    node_root = bundle / 'node'; node_root.mkdir()
    shutil.copy2(node, node_root / ('node' + suffix))
    for name in ('package.json', 'package-lock.json'):
        shutil.copy2(ROOT / 'vendor' / name, node_root / name)
    run(npm, 'ci', '--prefix', node_root, '--ignore-scripts', '--no-audit', '--no-fund')
    from scripts.patch_gentle import apply as patch_gentle
    patch_gentle(node_root / 'node_modules/gentle-pi')
    npm_stage = ROOT / 'build/native-npm'
    run(npm, 'install', '--prefix', npm_stage, '--ignore-scripts', '--no-save', '--package-lock=false', '--no-audit', '--no-fund', 'npm@11.19.0')
    shutil.copytree(npm_stage / 'node_modules/npm', node_root / 'node_modules/npm')
    gentle = node_root / 'node_modules/gentle-pi'
    run(node, ROOT / 'scripts/install-gentle-native.mjs', gentle)
    # The official resolver also verifies the native install's provenance.
    resolved = json.loads(run(node, ROOT / 'arise_app/resources/resolve-gentle-native.mjs', gentle, capture_output=True, text=True).stdout)
    native = Path(resolved['path']).resolve()
    if not native.is_relative_to(bundle.resolve()):
        raise RuntimeError('Gentle resolved outside the owned bundle')
    shutil.copytree(ROOT / 'vendor/forge-voice', bundle / 'forge-voice')
    stage_engram(bundle, identity)
    relative = lambda path: '@bundle/' + path.relative_to(bundle.resolve()).as_posix()
    manifest = {
        'owned_engine': 1, 'target': identity,
        'gentle_ai_bin': relative(native), 'engram_bin': '@bundle/engram/engram' + suffix,
        'memory_package': '@bundle/node/node_modules/gentle-engram',
        'web_package': '@bundle/node/node_modules/pi-web-access',
        'pi_command': ['@bundle/node/node' + suffix, '@bundle/node/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js'],
        'gentle_path': '@bundle/node/node_modules/gentle-pi', 'mcp': {},
        'versions': {'arise': __version__, 'pi': '1.5.2', 'gentle': '4.8.0', 'gentle_ai': '4.5.0', 'engram': '3.7.2', 'gentle_engram': '0.8.0'},
        'capabilities': {'desktop_tools_bundled': False, 'offline_models_bundled': False, 'automatic_updates': False},
    }
    (bundle / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    shutil.copy2(ROOT / 'docs/NATIVE-DISTRIBUTIONS.md', (package / 'Contents/Resources/README.txt' if mac else package / 'README.txt'))
    if not windows:
        public_bundle_permissions(package)
    if mac:
        info = package / 'Contents/Info.plist'
        with info.open('rb') as stream: metadata = plistlib.load(stream)
        metadata['CFBundleIdentifier'] = release['mac_id']
        metadata['CFBundleDisplayName'] = release['title']
        metadata['CFBundleName'] = release['title']
        metadata['CFBundleShortVersionString'] = __version__
        metadata['CFBundleVersion'] = __version__
        metadata['NSMicrophoneUsageDescription'] = 'ARISE uses the microphone for dictation and voice features you explicitly enable.'
        with info.open('wb') as stream: plistlib.dump(metadata, stream)
        # Added resources must be included in the final ad-hoc seal. Not notarization.
        run('codesign', '--force', '--sign', '-', application / 'ARISE-host')
        run('codesign', '--force', '--sign', '-', package)
        run('codesign', '--verify', '--deep', '--strict', package)
    run(sys.executable, ROOT / 'scripts/smoke_native.py', application, identity)
    output = ROOT / 'artifacts'; output.mkdir(exist_ok=True)
    stem = f"ARISE-{__version__}-{identity}-{release['channel']}"
    if mac:
        archive = output / (stem + '.zip')
        run('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', package, archive)
    else:
        archive = Path(shutil.make_archive(str(output / stem), 'zip' if windows else 'gztar', package.parent, package.name))
    digest = hashlib.sha256()
    with archive.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''): digest.update(block)
    (output / (stem + '.sha256')).write_text(digest.hexdigest() + '  ' + archive.name + '\n')
    print(archive)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--target', required=True)
    build(parser.parse_args().target)
