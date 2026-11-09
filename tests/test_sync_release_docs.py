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
        self.assertIn('iOS | Not published', table)
        self.assertIn('/android-qa-v0.2.0-qa)', table)

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
