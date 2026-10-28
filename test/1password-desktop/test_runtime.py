"""Root-only filesystem fixtures, run in disposable matrix containers."""
import importlib.util
import os
from pathlib import Path
import socket
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('configure', Path(__file__).parents[2] / 'src/1password-desktop/configure-runtime.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RuntimeEnvironmentTests(unittest.TestCase):
    def test_unset_and_canonical(self):
        for value in (None, '', '/run/user/1100'):
            self.assertEqual(module.expected_runtime(1100, value), '/run/user/1100')

    def test_other_runtime_rejected(self):
        for value in ('/tmp/runtime', '/run/user/12345', '/run/user/1100/../1100'):
            with self.assertRaises(ValueError):
                module.expected_runtime(1100, value)


@unittest.skipUnless(os.getuid() == 0, 'Root-only disposable-container fixtures')
class RuntimeFilesystemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.parent.chmod(0o755)
        self.runtime = self.parent / '1100'
        self.runtime.mkdir(mode=0o755)
        self.endpoint = self.runtime / module.SOCKET
        listener = socket.socket(socket.AF_UNIX)
        listener.bind(str(self.endpoint))
        listener.close()
        os.chown(self.endpoint, 1100, 1100)

    def prepare(self):
        module.prepare_runtime(1100, 1100, self.parent)

    def test_initialize_and_rerun(self):
        self.prepare()
        self.prepare()
        info = self.runtime.stat()
        self.assertEqual((info.st_uid, info.st_gid, info.st_mode & 0o777), (1100, 1100, 0o700))

    def test_existing_runtime_contents_preserved(self):
        self.prepare()
        other = self.runtime / 'unrelated'
        other.write_text('unchanged')
        self.prepare()
        self.assertEqual(other.read_text(), 'unchanged')

    def test_unrelated_root_directory_untouched(self):
        (self.runtime / 'unrelated').write_text('preserve')
        before = self.runtime.stat()
        with self.assertRaises(ValueError):
            self.prepare()
        after = self.runtime.stat()
        self.assertEqual((before.st_uid, before.st_mode), (after.st_uid, after.st_mode))

    def test_foreign_owner_refused(self):
        os.chown(self.runtime, 1200, 1200)
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(self.runtime.stat().st_uid, 1200)

    def test_existing_bad_mode_not_repaired(self):
        os.chown(self.runtime, 1100, 1100)
        self.runtime.chmod(0o755)
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(self.runtime.stat().st_mode & 0o777, 0o755)

    def test_wrong_socket_uid_refused(self):
        os.chown(self.endpoint, 1200, 1200)
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(self.runtime.stat().st_uid, 0)

    def test_socket_symlink_refused(self):
        self.endpoint.unlink()
        target = self.parent / 'target'
        target.write_text('preserve')
        self.endpoint.symlink_to(target)
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(target.read_text(), 'preserve')

    def test_runtime_symlink_refused(self):
        self.endpoint.unlink()
        self.runtime.rmdir()
        self.runtime.symlink_to(self.parent)
        with self.assertRaises(OSError):
            self.prepare()

    def test_unsafe_parent_refused(self):
        self.parent.chmod(0o777)
        with self.assertRaises(ValueError):
            self.prepare()

    def test_unsearchable_parent_refused(self):
        self.parent.chmod(0o700)
        with self.assertRaises(ValueError):
            self.prepare()

    def test_parent_symlink_refused(self):
        link = self.parent / 'alias'
        link.symlink_to(self.parent)
        with self.assertRaises(OSError):
            module.prepare_runtime(1100, 1100, link)

    def test_foreign_parent_refused(self):
        os.chown(self.parent, 1200, 1200)
        with self.assertRaises(ValueError):
            self.prepare()

    def test_missing_socket_refused(self):
        self.endpoint.unlink()
        with self.assertRaises(OSError):
            self.prepare()
        self.assertEqual(self.runtime.stat().st_uid, 0)


if __name__ == '__main__':
    unittest.main()
