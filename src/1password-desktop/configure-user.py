#!/usr/bin/python3
"""Resolve post-UID-update identity; drop root before accessing user files."""
import json
import os
import pwd
import stat
import sys


def reject_non_json_constant(_):
    raise ValueError('Non-JSON numeric constant in settings')


def configure_settings(home):
    # Descriptor-relative no-follow traversal prevents symlink races. All file
    # operations here run as the remote user, never as privileged container root.
    fd = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in ('.config', '1Password', 'settings'):
            try:
                os.mkdir(part, 0o700, dir_fd=fd)
            except FileExistsError:
                pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            if os.fstat(fd).st_uid != os.getuid():
                raise ValueError('Settings directory is not owned by remote user')
        name = 'settings.json'
        try:
            existing = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        except FileNotFoundError:
            data = {}
        else:
            with os.fdopen(existing) as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
                    raise ValueError('Unsafe settings ownership/type/link count')
                data = json.load(stream, parse_constant=reject_non_json_constant)
                if not isinstance(data, dict):
                    raise ValueError('Settings must be a JSON object')
        data['developers.cliSharedLockState.enabled'] = True
        temporary = '.feature-settings-' + os.urandom(12).hex()
        try:
            out = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            with os.fdopen(out, 'w') as stream:
                json.dump(data, stream)
                stream.write('\n')
            os.replace(temporary, name, src_dir_fd=fd, dst_dir_fd=fd)
        finally:
            try:
                os.unlink(temporary, dir_fd=fd)
            except FileNotFoundError:
                pass
    finally:
        os.close(fd)


def main():
    if len(sys.argv) != 1 or os.geteuid() != 0:
        raise ValueError('Run the installed helper via sudo without arguments')
    with open('/usr/local/share/1password-desktop/config.json') as stream:
        config = json.load(stream)
    user = pwd.getpwnam(config['user'])
    runtime = '/run/1password-desktop'
    fd = os.open(runtime, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if info.st_uid not in (0, user.pw_uid):
            raise ValueError('Unexpected runtime-directory owner')
        os.fchown(fd, user.pw_uid, user.pw_gid)
        os.fchmod(fd, 0o700)
    finally:
        os.close(fd)
    os.setgroups([])
    os.setgid(user.pw_gid)
    os.setuid(user.pw_uid)
    configure_settings(user.pw_dir)
    print('1password-desktop: remote-user configuration ready; no authentication performed')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Never include malformed settings content or personal paths in errors.
        print('1password-desktop: configuration failed; check user identity, directory ownership, symlinks, and settings JSON', file=sys.stderr)
        sys.exit(1)
