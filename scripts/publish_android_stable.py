"""Publish only release-signed Android artifacts; signing verification precedes this step."""
import json
import os
from pathlib import Path
import re
import subprocess


def main():
    if os.environ.get('GITHUB_REF_NAME') != 'main':
        raise RuntimeError('Stable Android requires main')
    source = Path('mobile/android/app/build.gradle').read_text(encoding='utf-8')
    version = re.search(r"if \(stableChannel\) versionName '([^']+)'", source)[1]
    if json.loads(Path('releases/stable.json').read_text(encoding='utf-8'))['android_version'] != version:
        raise RuntimeError('Android promotion version does not match source')
    code = int(re.search(r'versionCode (\d+)', source)[1])
    tag = 'android-v' + version
    assets = ['ARISE-Android.apk', 'ARISE-Android.apk.sha256', 'ARISE-Android.aab', 'ARISE-Android.aab.sha256']
    for path in assets:
        if not Path(path).is_file(): raise RuntimeError('Missing release artifact: ' + path)
    exists = subprocess.run(['gh', 'release', 'view', tag], capture_output=True).returncode == 0
    if exists:
        print('Stable Android version already exists; immutable artifacts retained.')
        return
    notes = Path('android-stable-notes.md')
    notes.write_text(f'# ARISE Companion {version}\n\nSigned stable Android companion. Requires Android 8+, Tailscale and an ARISE PC. This is not a standalone server or an iOS application. Stable and Preview have separate app IDs and require separate pairing. Wake detection remains opt-in and requires its configured model/key.\n')
    subprocess.run(['gh','release','create',tag,*assets,'--target',os.environ['GITHUB_SHA'],'--title',f'ARISE Android {version}','--notes-file',str(notes),'--latest=false'],check=True)
    manifest = dict(schema=1,applicationId='com.praxis.arise',channel='main',versionCode=code,versionName=version,
                    apkUrl=f'https://github.com/Maicololiveras/Arise/releases/download/{tag}/ARISE-Android.apk')
    Path('ARISE-Android-update.json').write_text(json.dumps(manifest)+'\n')
    if subprocess.run(['gh','release','view','android-stable'],capture_output=True).returncode != 0:
        subprocess.run(['gh','release','create','android-stable','--target',os.environ['GITHUB_SHA'],'--title','ARISE Android stable update feed','--notes','Versioned installers are immutable. This release contains only the current update pointer.','--latest=false'],check=True)
    subprocess.run(['gh','release','upload','android-stable','ARISE-Android-update.json','--clobber'],check=True)


if __name__ == '__main__': main()
