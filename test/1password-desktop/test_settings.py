import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('configure', Path(__file__).parents[2] / 'src/1password-desktop/configure-user.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.settings = self.home / '.config/1Password/settings/settings.json'

    def test_create_preserve_and_rerun(self):
        module.configure_settings(self.home)
        self.settings.write_text('{"unrelated":42}')
        module.configure_settings(self.home)
        module.configure_settings(self.home)
        self.assertEqual(json.loads(self.settings.read_text()), {'unrelated': 42, 'developers.cliSharedLockState.enabled': True})
        self.assertEqual(self.settings.stat().st_mode & 0o777, 0o600)

    def test_malformed_is_preserved(self):
        module.configure_settings(self.home)
        for content in ('{broken', '{"other":NaN}', '{"other":Infinity}'):
            with self.subTest(content=content):
                self.settings.write_text(content)
                with self.assertRaises(ValueError):
                    module.configure_settings(self.home)
                self.assertEqual(self.settings.read_text(), content)

    def test_symlink_refused(self):
        (self.home / '.config').symlink_to('/tmp')
        with self.assertRaises(OSError):
            module.configure_settings(self.home)

    def test_settings_symlink_refused(self):
        module.configure_settings(self.home)
        self.settings.unlink()
        target = self.home / 'target'
        target.write_text('{}')
        self.settings.symlink_to(target)
        with self.assertRaises(OSError):
            module.configure_settings(self.home)
        self.assertEqual(target.read_text(), '{}')

    def test_non_object_json_refused(self):
        module.configure_settings(self.home)
        for content in ('[]', 'null', 'true', '"text"', '42'):
            with self.subTest(content=content):
                self.settings.write_text(content)
                with self.assertRaises(ValueError):
                    module.configure_settings(self.home)
                self.assertEqual(self.settings.read_text(), content)

    def test_hardlink_refused(self):
        module.configure_settings(self.home)
        target = self.home / 'target'
        os.link(self.settings, target)
        original = target.read_bytes()
        with self.assertRaises(ValueError):
            module.configure_settings(self.home)
        self.assertEqual(target.read_bytes(), original)

    def test_fifo_refused_without_blocking(self):
        module.configure_settings(self.home)
        self.settings.unlink()
        os.mkfifo(self.settings)
        with self.assertRaises(ValueError):
            module.configure_settings(self.home)

    def test_directory_instead_of_settings_refused(self):
        module.configure_settings(self.home)
        self.settings.unlink()
        self.settings.mkdir()
        with self.assertRaises((ValueError, OSError)):
            module.configure_settings(self.home)

    def test_home_symlink_refused(self):
        link = self.home / 'home-link'
        link.symlink_to(self.home)
        with self.assertRaises(OSError):
            module.configure_settings(link)

    def test_permissive_mode_repaired(self):
        module.configure_settings(self.home)
        self.settings.chmod(0o666)
        module.configure_settings(self.home)
        self.assertEqual(self.settings.stat().st_mode & 0o777, 0o600)

    def test_no_temporary_files_left(self):
        module.configure_settings(self.home)
        self.assertEqual([p.name for p in self.settings.parent.iterdir()], ['settings.json'])

    @unittest.skipUnless(os.getuid() == 0, 'Root-only ownership fixture')
    def test_foreign_settings_owner_refused(self):
        module.configure_settings(self.home)
        os.chown(self.settings, 12345, -1)
        with self.assertRaises(ValueError):
            module.configure_settings(self.home)

    @unittest.skipUnless(os.getuid() == 0, 'Root-only ownership fixture')
    def test_foreign_directory_owner_refused(self):
        module.configure_settings(self.home)
        os.chown(self.settings.parent, 12345, -1)
        with self.assertRaises(ValueError):
            module.configure_settings(self.home)


if __name__ == '__main__':
    unittest.main()
