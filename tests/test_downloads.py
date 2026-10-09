import tempfile
import unittest
import zipfile
from pathlib import Path
from arise_app.downloads import safe_extract
class DownloadTests(unittest.TestCase):
    def test_zip_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            archive=Path(root)/'bad.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('../outside','bad')
            with self.assertRaises(ValueError):safe_extract(archive,Path(root)/'model')
            self.assertFalse((Path(root)/'outside').exists())
