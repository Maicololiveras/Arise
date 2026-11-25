"""Mobile trust domains derived exclusively from the installed desktop build."""
from enum import Enum
from pathlib import Path
import sys
from .updates import build_channel


class MobileChannel(Enum):
    PREVIEW = 'preview'
    STABLE = 'stable'

    @classmethod
    def installed(cls):
        if not (Path(__file__).parent/'resources/update-channel.json').is_file():
            if getattr(sys, 'frozen', False):
                raise RuntimeError('Falta la identidad de canal de esta instalación.')
            return cls.PREVIEW
        return {'qa':cls.PREVIEW, 'main':cls.STABLE}[build_channel()]

    @property
    def api(self):
        return f'/mobile/{self.value}/v1'

    @property
    def cookie(self):
        return f'__Host-arise-{self.value}-v1'

    @property
    def title(self):
        return 'ARISE Preview' if self is MobileChannel.PREVIEW else 'ARISE Estable'
