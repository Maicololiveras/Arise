import base64
import json
import unittest
from scripts.release_readme import update_readme, publish_metadata, START, END, REPO


def manifest(channel, version):
    tag = ('qa-v' if channel == 'qa' else 'v') + version
    return {'channel': channel, 'version': version, 'size': 400_000_000,
            'installer_url': f'{REPO}/releases/download/{tag}/ARISE-Setup.exe'}


class ReleaseReadmeTests(unittest.TestCase):
    def setUp(self):
        self.feeds = {'main': manifest('main', '0.4.8'), 'qa': manifest('qa', '0.4.10')}
        self.readme = '# ARISE\n\n## Instalar y configurar\n\nOld download\n\nPara actualizar una instalación existente, conserva tus datos.\n'

    def test_channel_links_use_published_versions_and_preserve_other_text(self):
        text = update_readme(self.readme, self.feeds)
        self.assertIn('/v0.4.8/ARISE-Setup.exe', text)
        self.assertIn('/qa-v0.4.10/ARISE-Setup.exe', text)
        self.assertNotIn('Old download', text)
        self.assertTrue(text.endswith('conserva tus datos.\n'))
        self.assertEqual(text.count(START), 1)
        self.assertEqual(text.count(END), 1)
        self.assertEqual(update_readme(text, self.feeds), text)

    def test_subsequent_release_replaces_previous_links(self):
        text = update_readme(self.readme, self.feeds)
        self.feeds['qa'] = manifest('qa', '0.4.11')
        text = update_readme(text, self.feeds)
        self.assertNotIn('qa-v0.4.10', text)
        self.assertIn('qa-v0.4.11', text)
        self.assertIn('/v0.4.8/', text)

    def test_cross_channel_or_external_download_is_rejected(self):
        self.feeds['qa']['installer_url'] = self.feeds['main']['installer_url']
        with self.assertRaises(ValueError): update_readme(self.readme, self.feeds)

    def fake_api(self, writes):
        def encoded(value):
            return {'content': base64.b64encode(value.encode()).decode()}
        def api(endpoint, payload=None, method='POST'):
            if payload is not None:
                writes.append((endpoint, payload, method))
                return {'sha': 'created'}
            if '/contents/updates/windows.json' in endpoint:
                return encoded(json.dumps(self.feeds[endpoint.split('ref=')[1]]))
            if '/git/ref/heads/' in endpoint: return {'object': {'sha': 'head'}}
            if '/git/commits/' in endpoint: return {'tree': {'sha': 'base'}}
            if '/contents/README.md' in endpoint: return encoded(self.readme)
            raise AssertionError(endpoint)
        return api

    def test_feed_and_readme_are_atomic_and_other_channel_feed_is_untouched(self):
        writes = []
        publish_metadata(self.fake_api(writes), 'main', manifest('main', '0.4.10'))
        trees = [p for e, p, m in writes if e.endswith('/git/trees')]
        self.assertEqual([entry['path'] for entry in trees[0]['tree']], ['README.md', 'updates/windows.json'])
        self.assertEqual([entry['path'] for entry in trees[1]['tree']], ['README.md'])
        refs = [(e, p, m) for e, p, m in writes if '/git/refs/heads/' in e]
        self.assertEqual(len(refs), 2)
        self.assertTrue(all(p['force'] is False and m == 'PATCH' for e, p, m in refs))

    def test_older_publication_never_moves_feed_backwards(self):
        writes = []
        with self.assertRaises(ValueError):
            publish_metadata(self.fake_api(writes), 'qa', manifest('qa', '0.4.9'))
        self.assertEqual(writes, [])
