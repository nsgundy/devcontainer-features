"""Run as root inside a disposable container, without network or host mounts."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import unittest

INSTALL = '/tests/src/1password-desktop/install.sh'
HELPER = '/usr/local/share/1password-desktop/configure-runtime.py'
RUNTIME = Path('/run/user/1100')
SETTINGS = Path('/home/featuretest/.config/1Password/settings/settings.json')


def run(*command, **kwargs):
    return subprocess.run(command, capture_output=True, text=True, timeout=15, **kwargs)


def user_run(*command):
    return run('runuser', '-u', 'featuretest', '--', *command)


class ContainerTests(unittest.TestCase):
    def setUp(self):
        RUNTIME.mkdir(parents=True, mode=0o755)
        endpoint = RUNTIME / '1Password-BrowserSupport.sock'
        listener = socket.socket(socket.AF_UNIX)
        listener.bind(str(endpoint))
        listener.close()
        os.chown(endpoint, 1100, 1100)
        SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS.write_text('malformed settings must stay untouched')
        SETTINGS.chmod(0o644)

    def tearDown(self):
        if RUNTIME.is_symlink():
            RUNTIME.unlink()
        elif RUNTIME.exists():
            shutil.rmtree(RUNTIME)

    def test_gid_validation(self):
        for value in ('', '-1', '+1', '1;id', '1 2', '1.0', '0', '4294967295',
                      '4294967296', '12345678901', '$(id)', '0x10', '1\n2'):
            with self.subTest(value=value):
                result = run('bash', INSTALL, env={**os.environ, 'HOSTCLIGID': value,
                             '_REMOTE_USER': 'featuretest'})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('hostCliGid', result.stderr)
                self.assertNotIn('apt-get', result.stdout)

    def test_gid_collision(self):
        original = Path('/etc/group').read_bytes()
        result = run('bash', INSTALL, env={**os.environ, 'HOSTCLIGID': '1100', '_REMOTE_USER': 'featuretest'})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('already allocated', result.stderr)
        self.assertEqual(Path('/etc/group').read_bytes(), original)

    def test_cli_mode(self):
        info = Path('/usr/bin/op').stat()
        self.assertEqual((info.st_uid, info.st_gid, info.st_mode & 0o7777), (0, 23456, 0o2755))

    def test_lifecycle_and_diagnostics_without_settings_mutation(self):
        before = (SETTINGS.read_bytes(), SETTINGS.stat().st_uid, SETTINGS.stat().st_mode)
        for _ in range(2):
            result = user_run(HELPER)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((SETTINGS.read_bytes(), SETTINGS.stat().st_uid, SETTINGS.stat().st_mode), before)
        self.assertEqual(RUNTIME.stat().st_uid, 1100)
        result = user_run('1password-desktop-doctor')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        fake = Path('/tmp/shadow-cli')
        fake.mkdir(exist_ok=True)
        (fake / 'op').write_text('#!/bin/sh\nexit 0\n')
        (fake / 'op').chmod(0o755)
        result = user_run('env', 'PATH=/tmp/shadow-cli:/usr/bin:/bin', '/usr/local/bin/1password-desktop-doctor')
        self.assertIn('FAIL: PATH selects packaged CLI', result.stdout)

    def test_doctor_reports_missing_runtime_without_traceback(self):
        shutil.rmtree(RUNTIME)
        result = user_run('1password-desktop-doctor')
        self.assertEqual(result.returncode, 1)
        self.assertIn('FAIL: Runtime directory exists', result.stdout)
        self.assertNotIn('Traceback', result.stderr)

    def test_doctor_detects_no_new_privileges(self):
        result = user_run('setpriv', '--no-new-privs', '1password-desktop-doctor')
        self.assertIn('FAIL: Set-GID execution allowed by process policy', result.stdout)

    def test_sudo_helper_rejects_arguments(self):
        result = user_run('sudo', '-n', HELPER, '/tmp/arbitrary-path')
        self.assertNotEqual(result.returncode, 0)

    def test_different_runtime_not_changed(self):
        before = RUNTIME.stat()
        result = user_run('env', 'XDG_RUNTIME_DIR=/tmp/other-runtime', HELPER)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(RUNTIME.stat().st_uid, before.st_uid)
        self.assertEqual(RUNTIME.stat().st_mode, before.st_mode)
        result = user_run('env', 'XDG_RUNTIME_DIR=/tmp/other-runtime', '1password-desktop-doctor')
        self.assertIn('FAIL: Existing runtime is unset or canonical', result.stdout)

    def test_missing_socket_not_initialized(self):
        (RUNTIME / '1Password-BrowserSupport.sock').unlink()
        result = user_run(HELPER)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(RUNTIME.stat().st_uid, 0)


if __name__ == '__main__':
    result = run('python3', '/tests/test/1password-desktop/test_runtime.py')
    print(result.stderr, end='')
    if result.returncode:
        raise SystemExit(result.returncode)
    unittest.main(verbosity=2)
