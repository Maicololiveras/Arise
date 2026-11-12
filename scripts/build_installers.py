"""Build and exercise native installers on disposable CI runners.

The application must already have passed build_native.py. --verify-install is
explicit because it installs/removes a package on the current machine.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from arise_app import __version__
from arise_app.platforms import target, data_directory


def run(*args):
    subprocess.run([str(a) for a in args], check=True, cwd=ROOT)


def write(path, content, mode=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    if mode is not None:
        path.chmod(mode)


def build(identity, verify=False):
    if target() != identity:
        raise RuntimeError('Installer must be built on the matching native target')
    from arise_app.distribution import native_release
    release = native_release()
    title, package_id, command = release['title'], release['linux_package'], release['command']
    system, arch = identity.split('-')
    output = ROOT / 'artifacts'
    output.mkdir(exist_ok=True)
    stem = f'ARISE-{__version__}-{identity}'
    stage = ROOT / 'build/installer'
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    if system == 'windows':
        compiler = shutil.which('ISCC') or str(Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'Inno Setup 6/ISCC.exe')
        run(compiler, '/Q', f'/DAppVersion={__version__}', f'/DAppTitle={title}', f"/DAppIdentity={release['windows_id']}", f"/DAppFolder={release['windows_dir']}", f'/DTargetArch={"x64os" if arch == "x64" else "arm64"}', f'/DTargetName={arch}', ROOT / 'packaging/ARISE-Native.iss')
        artifact = output / (stem + '-Setup.exe')
        installed = Path(os.environ['LOCALAPPDATA']) / ('Programs/' + release['windows_dir'])
        install = [artifact, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', f'/LOG={output / (identity + "-install.log")}']
        uninstall = [installed / 'unins000.exe', '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART']
        application = installed
    elif system == 'linux':
        package = stage / 'root'
        shutil.copytree(ROOT / 'dist/ARISE', package / ('opt/' + package_id), symlinks=True)
        cpu = 'amd64' if arch == 'x64' else 'arm64'
        write(package / 'DEBIAN/control', f'''Package: {package_id}
Version: {__version__}
Architecture: {cpu}
Maintainer: Maicol Oliveras <104401416+Maicololiveras@users.noreply.github.com>
Section: utils
Priority: optional
Depends: libc6 (>= 2.39), libstdc++6, libportaudio2, libegl1, libopengl0, libxcb-cursor0, libxkbcommon-x11-0, libxcb-icccm4, libxcb-keysyms1, libxcb-shape0
Description: {title} with its own Gentle Shell engine
 Native assistant Core package. Desktop MCP servers and offline models are not included.
''')
        write(package / ('usr/bin/' + command), f'#!/bin/sh\nexec /opt/{package_id}/ARISE "$@"\n', 0o755)
        write(package / ('usr/share/applications/' + command + '.desktop'), f'''[Desktop Entry]
Type=Application
Name={title}
Exec={command}
Icon={command}
Terminal=false
Categories=Utility;
''')
        icon = package / ('usr/share/icons/hicolor/256x256/apps/' + command + '.png')
        icon.parent.mkdir(parents=True)
        shutil.copy2(ROOT / 'assets/weg-logo.png', icon)
        artifact = output / (stem + '.deb')
        run('dpkg-deb', '--root-owner-group', '-Zxz', '-z1', '--build', package, artifact)
        installed = Path('/opt') / package_id
        application = installed
        install = ['sudo', 'dpkg', '-i', artifact]
        uninstall = ['sudo', 'dpkg', '-r', package_id]
    else:
        package = stage / 'root'
        app = package / ('Applications/' + title + '.app')
        app.parent.mkdir(parents=True)
        run('ditto', ROOT / 'dist/ARISE.app', app)
        components = stage / 'components.plist'
        run('pkgbuild', '--analyze', '--root', package, components)
        metadata = plistlib.loads(components.read_bytes())
        for item in metadata:
            item['BundleIsRelocatable'] = False
            item['BundleOverwriteAction'] = 'upgrade'
        components.write_bytes(plistlib.dumps(metadata))
        component = stage / 'component.pkg'
        run('pkgbuild', '--root', package, '--component-plist', components, '--identifier', release['mac_id'], '--version', __version__, '--install-location', '/', component)
        cpu = 'x86_64' if arch == 'x64' else 'arm64'
        distribution = stage / 'distribution.xml'
        write(distribution, f'''<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2">
<title>{title} {__version__}</title>
<options customize="never" require-scripts="false" hostArchitectures="{cpu}"/>
<volume-check><allowed-os-versions><os-version min="15.0"/></allowed-os-versions></volume-check>
<choices-outline><line choice="default"/></choices-outline>
<choice id="default" visible="false"><pkg-ref id="{release['mac_id']}"/></choice>
<pkg-ref id="{release['mac_id']}" version="{__version__}">component.pkg</pkg-ref>
</installer-gui-script>
''')
        artifact = output / (stem + '.pkg')
        run('productbuild', '--distribution', distribution, '--package-path', stage, artifact)
        installed = Path('/Applications') / (title + '.app')
        application = installed / 'Contents/Resources'
        install = ['sudo', 'installer', '-pkg', artifact, '-target', '/']
        uninstall = ['sudo', 'rm', '-rf', str(installed)]
    if verify:
        if installed.exists():
            raise RuntimeError(f'Refusing to replace an existing installation during CI verification: {installed}')
        # This profile belongs to the runner. Never overwrite an existing marker.
        marker = data_directory() / 'installer-preservation-check.txt'
        marker.parent.mkdir(parents=True, exist_ok=True)
        with marker.open('x', encoding='utf-8') as stream:
            stream.write('ARISE installer must preserve user data\n')
        expected = marker.read_bytes()
        run(*install)
        run(sys.executable, ROOT / 'scripts/smoke_native.py', application, identity)
        run(*install)  # Reinstall/upgrade path must preserve the profile.
        if marker.read_bytes() != expected:
            raise RuntimeError('Reinstall changed user data')
        run(*uninstall)
        if system == 'macos':
            run('sudo', 'pkgutil', '--forget', release['mac_id'])
        if (application / ('ARISE.exe' if system == 'windows' else 'ARISE-host')).exists():
            raise RuntimeError('Uninstall left the application executable behind')
        if marker.read_bytes() != expected:
            raise RuntimeError('Uninstall changed user data')
        marker.unlink()
        write(output / (identity + '-installer.json'), json.dumps({'target': identity, 'channel': release['channel'], 'version': __version__, 'install': 'passed', 'installed_engine_and_ui': 'passed', 'same_version_reinstall': 'passed', 'uninstall': 'passed', 'profile_preserved': True, 'physical_device_tested': False}, indent=2))
    digest = hashlib.file_digest(artifact.open('rb'), 'sha256').hexdigest()
    write(Path(str(artifact) + '.sha256'), digest + '  ' + artifact.name + '\n')
    print(artifact)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True)
    parser.add_argument('--verify-install', action='store_true')
    args = parser.parse_args()
    build(args.target, args.verify_install)
