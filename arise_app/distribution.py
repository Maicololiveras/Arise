"""Explicit identities for native Core stable and preview packages."""
import os


def native_release(channel=None):
    channel = channel or os.environ.get('ARISE_NATIVE_CHANNEL', 'preview')
    if channel not in ('stable', 'preview'):
        raise ValueError('Native channel must be stable or preview')
    stable = channel == 'stable'
    return dict(channel=channel, build_channel='main' if stable else 'qa',
                title='WEG Assistant',
                tag_prefix='weg-v',
                windows_dir='WEG-Assistant',
                windows_id='WEG.Assistant.Native',
                linux_package='weg-assistant',
                command='weg-assistant',
                mac_id='com.weg.assistant.preview')
