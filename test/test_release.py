"""Release guards run without credentials, network or Docker."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

spec = importlib.util.spec_from_file_location('release', Path(__file__).parents[1] / 'scripts/check_release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        source = self.root / 'src/1password-desktop'
        source.mkdir(parents=True)
        (source / 'devcontainer-feature.json').write_text(json.dumps({'version': '1.2.3'}))
        (self.root / 'releases').mkdir()
        self.notes = self.root / 'releases/1.2.3.md'
        self.notes.write_text('Release notes')

    def test_valid_release(self):
        self.assertEqual(release.validate(self.root, '1.2.3'), self.notes)

    def test_invalid_versions(self):
        for version in ('v1.2.3', '01.2.3', '1.2', '../1.2.3', '1.2.3-rc.1', '1.2.3\n'):
            with self.subTest(version=version), self.assertRaises(ValueError):
                release.validate(self.root, version)

    def test_metadata_mismatch(self):
        with self.assertRaises(ValueError):
            release.validate(self.root, '1.2.4')

    def test_missing_notes(self):
        self.notes.unlink()
        with self.assertRaises(ValueError):
            release.validate(self.root, '1.2.3')

    def test_empty_notes(self):
        self.notes.write_text(' \n')
        with self.assertRaises(ValueError):
            release.validate(self.root, '1.2.3')

    @patch.object(release, 'fetch', return_value=b'{}')
    def test_existing_version_refused(self, fetch):
        with self.assertRaises(ValueError):
            release.require_absent('https://example.test', {})

    @patch.object(release, 'fetch')
    def test_only_404_allows_publication(self, fetch):
        fetch.side_effect = urllib.error.HTTPError('https://example.test', 404, 'missing', {}, None)
        release.require_absent('https://example.test', {})
        for status in (401, 403, 429, 500):
            fetch.side_effect = urllib.error.HTTPError('https://example.test', status, 'failed', {}, None)
            with self.subTest(status=status), self.assertRaises(urllib.error.HTTPError):
                release.require_absent('https://example.test', {})

    @patch.dict('os.environ', {'GITHUB_REPOSITORY': 'someone/fork'})
    def test_wrong_repository_refused(self):
        with self.assertRaises(ValueError):
            release.check_remote('1.2.3')


if __name__ == '__main__':
    unittest.main()
