"""Find installed Windows Git for the private child without editing the system PATH."""
import os
from pathlib import Path
import shutil
import sys


def with_git(env, host):
    result = dict(env)
    if sys.platform != 'win32' or shutil.which('git', path=result.get('PATH', '')):
        return result
    candidates = [Path(host[key]) / suffix for key, suffix in (
        ('ProgramFiles', 'Git/cmd'), ('ProgramFiles(x86)', 'Git/cmd'),
        ('LOCALAPPDATA', 'Programs/Git/cmd')) if host.get(key)]
    for directory in candidates:
        if (directory / 'git.exe').is_file():
            result['PATH'] = str(directory) + os.pathsep + result.get('PATH', '')
            break
    return result
