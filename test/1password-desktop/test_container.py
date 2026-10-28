"""Run as root inside a disposable test container, without network or host mounts."""
import json
import os
from pathlib import Path
import subprocess
import unittest

INSTALL = '/tests/src/1password-desktop/install.sh'
HELPER = '/usr/local/share/1password-desktop/configure-user.py'
SETTINGS = Path('/home/featuretest/.config/1Password/settings/settings.json')
RUNTIME = Path('/run/1password-desktop')


def run(*command, **kwargs):
    return subprocess.run(command, capture_output=True, text=True, timeout=15, **kwargs)


def user_run(*command):
    return run('runuser', '-u', 'featuretest', '--', *command)


class ContainerTests(unittest.TestCase):
    def test_gid_validation(self):
        for value in ('', '-1', '+1', '1;id', '1 2', '1.0', '0', '4294967295',
                      '4294967296', '12345678901', '$(id)', '0x10', '1\n2'):
            with self.subTest(value=value):
                result = run('bash', INSTALL, env={**os.environ, 'HOSTCLIGID': value,
                             'ACCEPTRUNTIMEOVERRIDE': 'true', '_REMOTE_USER': 'featuretest'})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('hostCliGid', result.stderr)
                self.assertNotIn('apt-get', result.stdout)

    def test_gid_collision(self):
        original = Path('/etc/group').read_bytes()
        result = run('bash', INSTALL, env={**os.environ, 'HOSTCLIGID': '1100',
                     'ACCEPTRUNTIMEOVERRIDE': 'true', '_REMOTE_USER': 'featuretest'})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('already allocated', result.stderr)
        self.assertEqual(Path('/etc/group').read_bytes(), original)

    def test_runtime_override_requires_opt_in(self):
        result = run('bash', INSTALL, env={**os.environ, 'HOSTCLIGID': '23456',
                     'ACCEPTRUNTIMEOVERRIDE': 'false'})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('acceptRuntimeOverride=true', result.stderr)

    def test_cli_mode(self):
        info = Path('/usr/bin/op').stat()
        self.assertEqual((info.st_uid, info.st_gid, info.st_mode & 0o7777), (0, 23456, 0o2755))

    def test_lifecycle_and_diagnostics(self):
        for _ in range(2):
            result = user_run('sudo', '-n', HELPER)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(SETTINGS.stat().st_uid, 1100)
        self.assertEqual(SETTINGS.stat().st_mode & 0o777, 0o600)
        self.assertEqual(RUNTIME.stat().st_uid, 1100)
        result = user_run('1password-desktop-doctor')
        self.assertEqual(result.returncode, 1)
        self.assertIn('FAIL: Desktop socket exists', result.stdout)
        self.assertNotIn('Traceback', result.stderr)
        # A PATH-shadowing control is harmless and does not execute this fake CLI.
        fake = Path('/tmp/shadow-cli')
        fake.mkdir(exist_ok=True)
        (fake / 'op').write_text('#!/bin/sh\nexit 0\n')
        (fake / 'op').chmod(0o755)
        result = user_run('env', 'PATH=/tmp/shadow-cli:/usr/bin:/bin', '/usr/local/bin/1password-desktop-doctor')
        self.assertIn('FAIL: PATH selects packaged CLI', result.stdout)

    def test_doctor_reports_missing_runtime_without_traceback(self):
        info = RUNTIME.stat()
        RUNTIME.rmdir()
        try:
            result = user_run('1password-desktop-doctor')
            self.assertEqual(result.returncode, 1)
            self.assertIn('FAIL: Runtime directory exists', result.stdout)
            self.assertNotIn('Traceback', result.stderr)
        finally:
            RUNTIME.mkdir(mode=info.st_mode & 0o777)
            os.chown(RUNTIME, info.st_uid, info.st_gid)

    def test_doctor_detects_no_new_privileges(self):
        result = user_run('setpriv', '--no-new-privs', '1password-desktop-doctor')
        self.assertIn('FAIL: Set-GID execution allowed by process policy', result.stdout)

    def test_sudo_helper_rejects_arguments(self):
        result = user_run('sudo', '-n', HELPER, '/tmp/arbitrary-path')
        self.assertNotEqual(result.returncode, 0)

    def test_runtime_symlink_refused(self):
        # OverlayFS cannot rename a lower-layer directory (EXDEV). This empty
        # runtime fixture can instead be removed/recreated without privileges
        # beyond the disposable container root already used for this test.
        original_runtime = RUNTIME.stat()
        RUNTIME.rmdir()
        target = Path('/tmp/runtime-target')
        target.mkdir()
        original = target.stat()
        try:
            RUNTIME.symlink_to(target)
            result = run(HELPER)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(target.stat().st_uid, original.st_uid)
            self.assertEqual(target.stat().st_mode, original.st_mode)
        finally:
            RUNTIME.unlink()
            RUNTIME.mkdir(mode=original_runtime.st_mode & 0o777)
            os.chown(RUNTIME, original_runtime.st_uid, original_runtime.st_gid)


if __name__ == '__main__':
    # Includes root-only malicious-ownership fixtures; no desktop app is used.
    result = run('python3', '/tests/test/1password-desktop/test_settings.py')
    print(result.stderr, end='')
    if result.returncode:
        raise SystemExit(result.returncode)
    unittest.main(verbosity=2)
