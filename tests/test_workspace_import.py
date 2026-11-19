import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from arise_app.attachments import import_workspace_files


class WorkspaceImports(unittest.TestCase):
    def test_names_and_bytes_survive_without_overwrites(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a, b, workspace = [root / k for k in ('a', 'b', 'workspace')]
            for folder in (a, b, workspace):
                folder.mkdir()
            sources = [a / 'datos.xlsx', b / 'datos.xlsx']
            for idx, src in enumerate(sources):
                src.write_bytes(bytes([idx]))
            refs = import_workspace_files(workspace, sources)
            self.assertNotEqual(refs[0], refs[1])
            self.assertEqual([p.read_bytes() for p in sources], [(workspace / r).read_bytes() for r in refs])
            self.assertNotEqual(refs, import_workspace_files(workspace, sources))

    def test_size_and_partial_failure_leave_workspace_empty(self):
        with tempfile.TemporaryDirectory() as temp:
            src = Path(temp) / 'sample'
            src.write_bytes(b'123')
            workspace = Path(temp) / 'workspace'
            workspace.mkdir()
            with self.assertRaises(ValueError):
                import_workspace_files(workspace, [src], max_bytes=2)
            original = Path.open
            def fail_write(path, mode, *args, **kwargs):
                if mode == 'xb' and '(2)' in path.name:
                    raise OSError('disk full')
                return original(path, mode, *args, **kwargs)
            with patch.object(Path, 'open', fail_write), self.assertRaises(OSError):
                import_workspace_files(workspace, [src, src])
            self.assertEqual(list(workspace.iterdir()), [])
