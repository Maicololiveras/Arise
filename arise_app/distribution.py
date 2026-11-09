"""Explicit identities for native Core stable and preview packages."""
import os


def native_release(channel=None):
    channel = channel or os.environ.get('ARISE_NATIVE_CHANNEL', 'preview')
    if channel not in ('stable', 'preview'):
        raise ValueError('Native channel must be stable or preview')
    stable = channel == 'stable'
    return dict(channel=channel, build_channel='main' if stable else 'qa',
                title='ARISE Core' if stable else 'ARISE Preview',
                tag_prefix='native-stable-v' if stable else 'native-v',
                windows_dir='ARISE-Native' if stable else 'ARISE-Native-Preview',
                windows_id='PRAXISGENAI.ARISE.Native' if stable else 'PRAXISGENAI.ARISE.NativePreview',
                linux_package='arise-native' if stable else 'arise-native-preview',
                command='arise' if stable else 'arise-preview',
                mac_id='com.praxisgenai.arise.core' if stable else 'com.praxisgenai.arise.preview')
