import unittest
from scripts.sync_release_docs import published_catalog, render_catalog, replace_block


def release(tag, names, **extra):
    return dict(tag_name=tag, published_at='2026-11-09', draft=False,
                assets=[dict(name=name, size=123) for name in names], **extra)


class PublishedDocsTests(unittest.TestCase):
    def test_excludes_drafts_incomplete_and_unpublished(self):
        names = ['ARISE-Setup.exe', 'ARISE-Setup.exe.sha256']
        good = release('v0.4.37', names)
        draft = dict(release('v0.4.40', names), draft=True)
        incomplete = release('v0.4.41', names[:1])
        unpublished = dict(release('v0.4.42', names), published_at=None)
        catalog = published_catalog([good, draft, incomplete, unpublished])
        self.assertEqual(catalog['stable']['version'], '0.4.37')

    def test_products_are_independent_and_semantically_ordered(self):
        names = ['ARISE-Setup.exe', 'ARISE-Setup.exe.sha256']
        catalog = published_catalog([release('qa-v0.4.9', names), release('qa-v0.4.10', names),
            release('v0.4.8', names), release('android-qa-v0.2.0-qa',
            ['ARISE-Android-QA.apk', 'ARISE-Android-QA.apk.sha256'])])
        self.assertEqual(catalog['preview']['version'], '0.4.10')
        self.assertEqual(catalog['android']['version'], '0.2.0-qa')
        table = render_catalog(catalog)
        self.assertIn('| iOS / iPadOS | Mobile companion | Not released | Not released |', table)
        self.assertIn('/android-qa-v0.2.0-qa/ARISE-Android-QA.apk)', table)

    def test_requires_all_native_architectures(self):
        names = [f'ARISE-0.4.39-{os}-{arch}{ext}' for os, ext in
                 (('windows', '-Setup.exe'), ('linux', '.deb'), ('macos', '.pkg'))
                 for arch in ('x64', 'arm64')]
        assets = names + [n + '.sha256' for n in names]
        self.assertIn('native', published_catalog([release('native-v0.4.39', assets)]))
        self.assertNotIn('native', published_catalog([release('native-v0.4.39', assets[:-1])]))

    def test_idempotent_and_preserves_history(self):
        source = '# Install\n\nIntroduced in 0.4.36.\n'
        block = render_catalog({})
        updated = replace_block(source, block)
        self.assertEqual(updated, replace_block(updated, block))
        self.assertIn('Introduced in 0.4.36.', updated)

    def test_instruction_links_resolve_in_root_and_nested_guides(self):
        from pathlib import Path
        root = render_catalog({})
        readme = Path('README.md').read_text()
        for system in ('windows', 'linux', 'macos', 'android', 'ios'):
            self.assertIn(f'(#install-{system})', root)
            self.assertIn(f'<a id="install-{system}"></a>', readme)
        nested = render_catalog({}, 'https://github.com/Maicololiveras/Arise/blob/main/README.md')
        self.assertIn('/README.md#install-linux)', nested)
        self.assertNotIn('](#install-', nested)

    def test_windows_publisher_preserves_other_platforms_and_video(self):
        from scripts.release_readme import update_readme
        names = ['ARISE-Setup.exe', 'ARISE-Setup.exe.sha256']
        source = render_catalog(published_catalog([release('v0.4.8', names), release('qa-v0.4.9', names)]))
        source += '\n<!-- arise-video:start -->\nvideo-url\n<!-- arise-video:end -->'
        manifests = {channel:dict(channel=channel, version=version, size=123,
            installer_url=f'https://github.com/Maicololiveras/Arise/releases/download/{tag}/ARISE-Setup.exe')
            for channel, version, tag in [('main','0.4.8','v0.4.8'),('qa','0.4.10','qa-v0.4.10')]}
        updated = update_readme(source, manifests)
        self.assertIn('[Complete 0.4.10]', updated)
        self.assertIn('[Complete 0.4.8]', updated)
        self.assertNotIn('qa-v0.4.9', updated)
        self.assertIn('| Android 8+', updated)
        self.assertTrue(updated.endswith('video-url\n<!-- arise-video:end -->'))
        self.assertEqual(updated, update_readme(updated, manifests))

    def test_native_publisher_updates_core_labels_only(self):
        from scripts.release_readme import native_downloads
        source = '[Core 0.4.38](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.38/ARISE-0.4.38-linux-x64.deb) [Complete 0.4.37](unchanged)'
        updated = native_downloads(source, '0.4.39', [], None)
        self.assertIn('[Core 0.4.39]', updated)
        self.assertIn('[Complete 0.4.37]', updated)
