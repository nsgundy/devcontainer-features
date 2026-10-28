#!/usr/bin/python3
"""Validate the existing runtime; initialize only a socket-only mount directory."""
import json
import os
import pwd
import stat
import subprocess
import sys

SOCKET = '1Password-BrowserSupport.sock'


def expected_runtime(uid, value):
    canonical = f'/run/user/{uid}'
    if value and value != canonical:
        raise ValueError('Existing XDG_RUNTIME_DIR differs from the canonical socket path; it was not changed')
    return canonical


def prepare_runtime(uid, gid, parent='/run/user'):
    # Docker creates mount parents as root. Never follow symlinks or change
    # ownership of a directory containing anything other than this socket.
    fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if info.st_uid != 0 or stat.S_IMODE(info.st_mode) & 0o022 or not info.st_mode & stat.S_IXOTH:
            raise ValueError('Runtime parent must be root-owned, searchable, and not group/world writable')
        child = os.open(str(uid), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
    finally:
        os.close(fd)
    try:
        socket = os.stat(SOCKET, dir_fd=child, follow_symlinks=False)
        if not stat.S_ISSOCK(socket.st_mode) or socket.st_uid != uid:
            raise ValueError('Socket must be a socket owned by the final remote UID')
        info = os.fstat(child)
        if info.st_uid == uid:
            if stat.S_IMODE(info.st_mode) != 0o700:
                raise ValueError('Existing user runtime must have mode 0700; it was not changed')
        elif info.st_uid == 0:
            if set(os.listdir(child)) != {SOCKET}:
                raise ValueError('Refusing to take ownership of an unrelated runtime directory')
            os.fchown(child, uid, gid)
            os.fchmod(child, 0o700)
        else:
            raise ValueError('Runtime directory has an unexpected owner; it was not changed')
    finally:
        os.close(child)


def main():
    if len(sys.argv) != 1:
        raise ValueError('No arguments are accepted')
    with open('/usr/local/share/1password-desktop/config.json') as stream:
        config = json.load(stream)
    user = pwd.getpwnam(config['user'])
    expected_runtime(user.pw_uid, os.environ.get('XDG_RUNTIME_DIR'))
    if os.geteuid() != 0:
        if os.getuid() != user.pw_uid:
            raise ValueError('Run as the configured remote user')
        # Sudo resets environment; validate the caller's runtime before entering
        # the root helper. The privileged helper has only a fixed-path operation.
        result = subprocess.run(['sudo', '-n', '/usr/local/share/1password-desktop/configure-runtime.py'], check=False)
        raise SystemExit(result.returncode)
    prepare_runtime(user.pw_uid, user.pw_gid)
    print('1password-desktop: canonical runtime validated; environment and user settings unchanged')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError):
        print('1password-desktop: incompatible runtime/socket; require matching UID, canonical /run/user/<uid> socket, and an unset or matching XDG_RUNTIME_DIR. Existing ownership, permissions and symlinks must be safe.', file=sys.stderr)
        sys.exit(1)
