#!/usr/bin/python3
"""Local metadata diagnostics only; never authenticate or read account data."""
import json
import os
import pathlib
import shutil
import stat
import subprocess

errors = []
def check(label, condition):
    print(('OK: ' if condition else 'FAIL: ') + label)
    if not condition:
        errors.append(label)

with open('/usr/local/share/1password-desktop/config.json') as stream:
    config = json.load(stream)
selected = shutil.which('op')
check('PATH selects packaged CLI', selected is not None and os.path.realpath(selected) == os.path.realpath('/usr/bin/op'))
info = os.stat('/usr/bin/op')
check('CLI root ownership, configured GID and mode 2755', info.st_uid == 0 and info.st_gid == config['gid'] and stat.S_IMODE(info.st_mode) == 0o2755)
version = subprocess.run(['/usr/bin/op', '--version'], capture_output=True, text=True, timeout=5)
check('Packaged CLI version command works', version.returncode == 0)
status = pathlib.Path('/proc/self/status').read_text()
no_new_privs = next((line.split(':', 1)[1].strip() for line in status.splitlines()
                     if line.startswith('NoNewPrivs:')), None)
check('Set-GID execution allowed by process policy', no_new_privs == '0')
check('CLI filesystem allows set-GID', not (os.statvfs('/usr/bin/op').f_flag & os.ST_NOSUID))
runtime = pathlib.Path('/run/1password-desktop')
check('Expected runtime environment', os.environ.get('XDG_RUNTIME_DIR') == str(runtime))
exists = runtime.is_dir() and not runtime.is_symlink()
check('Runtime directory exists', exists)
if exists:
    check('Runtime owned by current user', runtime.stat().st_uid == os.getuid())
    check('Runtime writable by current user', os.access(runtime, os.W_OK))
socket = runtime / '1Password-BrowserSupport.sock'
check('Desktop socket exists', socket.is_socket())
if socket.is_socket():
    check('Desktop socket UID matches current user', socket.stat().st_uid == os.getuid())
settings = pathlib.Path.home() / '.config/1Password/settings/settings.json'
try:
    info = settings.lstat()
    safe = stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o600
    check('Settings safe ownership, type and mode', safe)
    if safe:
        with settings.open() as stream:
            check('Desktop integration setting enabled', json.load(stream).get('developers.cliSharedLockState.enabled') is True)
except (OSError, ValueError, AttributeError):
    check('Settings present and valid JSON object', False)
print('No authentication or secret reads performed. Desktop authorization still requires separate integration checks.')
raise SystemExit(1 if errors else 0)
