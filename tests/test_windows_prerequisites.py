import os
from pathlib import Path
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from arise_app import windows_prerequisites as p
from arise_app.gentle_setup import install_gentle

class WindowsPrerequisitesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'bundle'
        self.data = self.root / 'data'
        self.data.mkdir()
        self.env = {'SystemRoot': str(self.root / 'Windows'), 'LOCALAPPDATA': str(self.root / 'Local'), 'PATH': ''}
        self.files = ['node/node.exe', 'node/node_modules/npm/bin/npm-cli.js']
        for name in self.files:
            path = self.bundle / name; path.parent.mkdir(parents=True, exist_ok=True); path.touch()
        tar = self.root / 'Windows/System32/tar.exe'; tar.parent.mkdir(parents=True); tar.touch()
        self.managers()
        self.git = self.root / 'Git/cmd/git.exe'
        self.bash = self.root / 'Git/bin/bash.exe'
        self.go = self.root / 'Go/bin/go.exe'

    def managers(self):
        for name in ('node_modules/pnpm/bin/pnpm.mjs', 'node_modules/npm/bin/npm-cli.js', 'pnpm.cmd', 'npm.cmd'):
            path = self.data / 'package-managers' / name
            path.parent.mkdir(parents=True, exist_ok=True); path.touch()

    def probe(self, cmd, env, cwd):
        path = str(cmd[1]) if len(cmd) > 2 else str(cmd[0])
        if path.endswith('pnpm.mjs'): return p.PNPM_VERSION
        if path.endswith('npm-cli.js'): return p.NPM_VERSION
        if path.endswith('node.exe'): return 'v24.13.1'
        if path.endswith('tar.exe'): return 'bsdtar 3.8.1'
        return ''

    def prepare(self):
        return p.prepare_prerequisites(self.bundle, self.data, env=self.env)

    def test_reuse_is_idempotent_and_passes_paths_to_child_only(self):
        before = dict(self.env)
        with patch.object(p, 'probe', side_effect=self.probe), patch.object(p, 'find_git', return_value=(self.git,self.bash)), patch.object(p, 'find_go', return_value=self.go), patch.object(p, 'checked_run') as run:
            first = self.prepare(); second = self.prepare()
        run.assert_not_called()
        self.assertEqual(first, second); self.assertEqual(self.env, before)
        paths = first['PATH'].split(os.pathsep)
        self.assertEqual(paths[:2], [str(self.bundle/'node'), str(self.data/'package-managers')])
        self.assertIn(str(self.git.parent), paths); self.assertIn(str(self.go.parent), paths)

    def test_missing_native_tools_install_then_reprobe(self):
        installed = []
        def install(tool, env, cwd, notify): installed.append(tool)
        with patch.object(p, 'probe', side_effect=self.probe), patch.object(p, 'find_git', side_effect=[None,(self.git,self.bash)]), patch.object(p, 'find_go', side_effect=[None,self.go]), patch.object(p, 'install_native', side_effect=install):
            self.prepare()
        self.assertEqual(installed, ['Git','Go'])

    def test_install_success_without_usable_binary_is_not_ready(self):
        with patch.object(p, 'probe', side_effect=self.probe), patch.object(p, 'find_git', return_value=None), patch.object(p, 'install_native'), patch.object(p, 'find_go') as go:
            with self.assertRaisesRegex(RuntimeError, 'Git sigue ausente'): self.prepare()
        go.assert_not_called()

    def test_missing_tar_stops_before_any_install(self):
        (self.root/'Windows/System32/tar.exe').unlink()
        with patch.object(p, 'probe', side_effect=self.probe), patch.object(p, 'install_native') as install:
            with self.assertRaisesRegex(RuntimeError, 'tar.exe'): self.prepare()
        install.assert_not_called()

    def test_incompatible_node_stops_before_any_install(self):
        def old(cmd, env, cwd): return 'v22.19.0' if str(cmd[0]).endswith('node.exe') else self.probe(cmd,env,cwd)
        with patch.object(p, 'probe', side_effect=old), patch.object(p, 'install_native') as install:
            with self.assertRaisesRegex(RuntimeError, 'Node/npm'): self.prepare()
        install.assert_not_called()

    def test_missing_managers_install_pinned_private_prefix_without_scripts(self):
        ready = False
        def output(cmd, env, cwd):
            if 'package-managers' in str(cmd) and not ready: return ''
            return self.probe(cmd,env,cwd)
        def install(cmd, label, **kwargs):
            nonlocal ready
            self.assertIn('--ignore-scripts',cmd); self.assertIn('pnpm@11.1.1',cmd)
            self.assertEqual(cmd[cmd.index('--prefix')+1],str(self.data/'package-managers'))
            ready = True
        with patch.object(p, 'probe', side_effect=output), patch.object(p, 'find_git', return_value=(self.git,self.bash)), patch.object(p, 'find_go', return_value=self.go), patch.object(p, 'checked_run', side_effect=install) as run:
            self.prepare()
        run.assert_called_once()

    def test_missing_winget_gives_manual_command(self):
        with patch.object(p, 'find_native', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'winget install --id Git.Git'):
                p.install_native('Git',self.env,self.data,lambda _:None)

    def test_winget_failure_blocks_instead_of_starting_wizard(self):
        with patch.object(p, 'find_native', return_value=self.root/'winget.exe'), patch.object(p, 'checked_run', side_effect=RuntimeError('cancelado')):
            with self.assertRaisesRegex(RuntimeError, 'Gentle Shell no se inició'):
                p.install_native('Go',self.env,self.data,lambda _:None)
        source=self.bundle/'gentle-installer/scripts/bootstrap.cmd';source.parent.mkdir(parents=True);source.touch()
        runtime=SimpleNamespace(transition_lock=threading.RLock(),busy=False,voice_service=None,disconnect=Mock(),storage=SimpleNamespace(root=self.data),emit=Mock())
        with patch('arise_app.gentle_setup.os', SimpleNamespace(name='nt',environ=self.env)), patch('arise_app.gentle_setup.application_root',return_value=self.root), patch.object(p,'prepare_prerequisites',side_effect=RuntimeError('requisitos pendientes')), patch('arise_app.gentle_setup.subprocess.Popen') as launch:
            with self.assertRaisesRegex(RuntimeError,'requisitos pendientes'):install_gentle(runtime)
        launch.assert_not_called()
        self.assertFalse((self.data/'installers').exists())

    def test_git_without_bash_is_not_accepted_and_old_go_is_skipped(self):
        for path in (self.git,self.go):path.parent.mkdir(parents=True,exist_ok=True);path.touch()
        env={**self.env,'PATH':os.pathsep.join([str(self.git.parent),str(self.go.parent)])}
        with patch.object(p,'probe',side_effect=lambda cmd,*_: 'git version 2.51.0.windows.1' if str(cmd[0]).endswith('git.exe') else 'go version go1.24.0 windows/amd64'):
            self.assertIsNone(p.find_git(env,self.data));self.assertIsNone(p.find_go(env,self.data))
        self.bash.parent.mkdir(parents=True);self.bash.touch()
        with patch.object(p,'probe',side_effect=lambda cmd,*_: 'git version 2.51.0.windows.1' if str(cmd[0]).endswith('git.exe') else 'GNU bash, version 5.2'):
            self.assertEqual(p.find_git(env,self.data),(self.git,self.bash))
