#!/usr/bin/python3
"""Local metadata diagnostics only; never authenticate or read account data."""
import json
import os
import pathlib
import pwd
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
user = pwd.getpwnam(config['user'])
check('Running as configured remote user', os.getuid() == user.pw_uid)
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
runtime = pathlib.Path(f'/run/user/{user.pw_uid}')
check('Existing runtime is unset or canonical', not os.environ.get('XDG_RUNTIME_DIR') or os.environ['XDG_RUNTIME_DIR'] == str(runtime))
check('Desktop integration toggle enabled', os.environ.get('OP_BIOMETRIC_UNLOCK_ENABLED') == 'true')
exists = runtime.is_dir() and not runtime.is_symlink()
check('Runtime directory exists', exists)
if exists:
    info = runtime.stat()
    check('Runtime owned by remote user with mode 0700', info.st_uid == user.pw_uid and stat.S_IMODE(info.st_mode) == 0o700)
    check('Runtime writable by current user', os.access(runtime, os.W_OK))
    socket = runtime / '1Password-BrowserSupport.sock'
    try:
        info = socket.lstat()
        check('Desktop socket exists', stat.S_ISSOCK(info.st_mode))
        check('Desktop socket UID matches remote user', info.st_uid == user.pw_uid)
    except OSError:
        check('Desktop socket exists', False)
else:
    check('Desktop socket exists', False)
print('No authentication or secret reads performed. User settings were not accessed. Desktop authorization requires a separate integration test.')
raise SystemExit(1 if errors else 0)
