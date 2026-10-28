# 1Password desktop integration

Experimental Feature for native Linux, local rootful Docker without user namespace
remapping, Debian/Ubuntu apt images, and matching desktop/container UID. Requires
working host desktop CLI integration and normal set-GID execution. Other host
platforms, rootless Docker, remote daemons and Codespaces are unsupported.

## Options

- `hostCliGid`: required decimal GID from host `stat -c %g /usr/bin/op`.
  Zero/reserved/out-of-range values are rejected. An unrelated group already
  using this GID causes installation to fail; no groups are modified.
- `acceptRuntimeOverride`: must explicitly be `true` for version 0.1.0. It accepts
  the global container `XDG_RUNTIME_DIR=/run/1password-desktop` override. Do not
  enable this if it would replace another working runtime integration.

The host must export `XDG_RUNTIME_DIR` into VS Code's environment. A missing
socket source can prevent container creation before diagnostics execute.

## Behavior

Installs the latest official signed apt CLI, Python 3, sudo, curl, GnuPG and CA
certificates. CLI ownership is root/configured numeric GID, mode 2755.
Only `${localEnv:XDG_RUNTIME_DIR}/1Password-BrowserSupport.sock` is mounted, at
`/run/1password-desktop/1Password-BrowserSupport.sock`.

The postStart helper resolves the remote username after UID updates, sets the
dedicated runtime directory's owner/mode, then drops privileges before updating
only `developers.cliSharedLockState.enabled` in the user's settings. Unrelated
settings are preserved. Malformed/non-object JSON, unsafe ownership, symlinks
and hardlinked settings are refused. Settings mode is enforced as 0600.

No host accounts, sessions or settings are copied. Authentication, account
listing and secret reads never run automatically. Mise or other PATH shims must
not shadow `/usr/bin/op`; this Feature does not modify dotfiles or wrap `op`.

## Security and owned files

Trust the container: socket access is not per-secret isolation, and ordinary
container root can manipulate numeric identities. Desktop authorization still
applies. No privileged mode, extra capabilities, host PID/network sharing, or
broad runtime-directory mounts are requested.

Feature-owned paths:

- `/usr/local/share/1password-desktop/`: root-owned helper and configuration.
- `/usr/local/bin/1password-desktop-doctor`.
- `/etc/sudoers.d/1password-desktop`: permits only the exact no-argument helper.
  Any user can invoke it, but it always configures the fixed remote user and
  drops privileges before accessing user files.
- `/run/1password-desktop`: dedicated runtime/cache directory and socket mount.
- Official apt keyrings, source and signature policy.
- The integration boolean in `~/.config/1Password/settings/settings.json`.

## Diagnostics, recovery and rollback

Run `1password-desktop-doctor` as the remote user. It checks PATH, CLI permissions,
runtime ownership/writability, socket UID, minimal settings, NoNewPrivs and the
CLI filesystem's nosuid flag. It never authenticates, dumps settings, or reads
accounts/secrets. These checks do not prove desktop authorization works or rule
out every execution-policy restriction.

App restart may replace the socket inode, leaving a single-file bind mount stale.
Recreate the container to recover; restarting it may retain the stale mount.

Rollback: remove the Feature reference and rebuild. With a persistent home,
remove only its integration boolean; delete the settings file only if no other
keys remain. No host configuration requires rollback.

## Personal default Features: limitations

Actual VS Code User defaultFeatures injection passed in disposable Dockerfile
and Compose fixtures with lockfile handling disabled, preserving project files
and existing empty lockfiles. This is not a recommendation to globally disable
lockfile handling: doing so also disables generation/verification for project
Features. Behavior with published additional Features and normal lockfile
handling is under investigation.

The global runtime override can affect D-Bus, Wayland, audio and other tools.
Preserving an existing runtime or scoping the variable to explicit CLI consumers
is under investigation. Cache reuse/expiry and end-to-end secret retrieval have
not been established; no test secret reads have been performed.
