import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication

class WegIdentityTests(unittest.TestCase):
    def test_identity_and_both_orb_modes(self):
        from arise_app.updates import application_name, check_update
        from arise_app.orb import build_orb
        from arise_app.brand import icon_image
        app=QApplication.instance() or QApplication([])
        self.assertEqual(application_name(),'WEG Assistant')
        for mode in ('sprite','procedural'):
            _,orb=build_orb(app,96,0,0,mode)
            self.assertEqual(orb.windowTitle(),'WEG Assistant')
            self.assertEqual(len(orb.frames),1);orb.close()
        self.assertEqual(icon_image(96).width(),96)
        with patch('arise_app.updates.open_https',side_effect=AssertionError('no ARISE feed')):
            self.assertIsNone(check_update())

    def test_weg_release_is_excluded_from_public_arise_catalog(self):
        from scripts.sync_release_docs import published_catalog
        self.assertEqual(published_catalog([{'tag_name':'weg-v0.4.44','published_at':'2026-11-12','assets':[]}]),{})

    def test_publisher_only_targets_weg_and_never_updates_arise_metadata(self):
        from scripts import publish_native
        with patch.dict('os.environ',GITHUB_REF_NAME='qa'):
            with self.assertRaisesRegex(RuntimeError,'only from weg'):
                publish_native.main('unused')
        source=Path(publish_native.__file__).read_text()
        self.assertNotIn('publish_native_metadata',source)
