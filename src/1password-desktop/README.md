# 1Password desktop integration

**0.2.0 development design; not published or desktop-authentication validated.**

Supports native Linux, local rootful Docker without user namespace remapping,
Debian/Ubuntu apt images, and matching desktop/container UID. Requires working
host desktop CLI integration, canonical host runtime `/run/user/<uid>`, and
normal set-GID execution. Other host platforms, rootless Docker, remote daemons
and Codespaces are unsupported.

## Option

`hostCliGid`: required decimal GID from host `stat -c %g /usr/bin/op`.
Zero/reserved/out-of-range values are rejected. An unrelated group already
using this GID causes installation to fail; no groups are modified.

The host must export canonical `XDG_RUNTIME_DIR` into VS Code's environment.
Only its `1Password-BrowserSupport.sock` is mounted, at the same container path.
A missing source may prevent container creation before diagnostics execute.

## Runtime-preserving behavior

Unlike 0.1.0, this design **does not set XDG_RUNTIME_DIR, write user settings, or
require acceptRuntimeOverride**. It sets only the documented CLI integration
toggle `OP_BIOMETRIC_UNLOCK_ENABLED=true`.

The container's XDG_RUNTIME_DIR must be unset/empty or exactly `/run/user/<uid>`
for the final remote UID. Current official CLI endpoint-selection probes follow
that path when the variable is unset. An existing different runtime is rejected,
not overridden. Only canonical host runtime paths are supported for now.

After UID updates, the lifecycle helper checks the expected socket type/UID and
runtime ownership. An already user-owned mode-0700 runtime is preserved, including
unrelated contents. A root-owned mount-parent directory is initialized only if
its **sole entry is this user's socket**. Foreign owners, symlinks, unsafe parent
permissions, incompatible runtimes and missing/wrong-UID sockets are rejected.
No recursive ownership changes or modifications to the `/run/user` parent occur.

The helper has a narrow passwordless sudo rule for its exact no-argument
invocation; it only operates on the configured remote user's canonical directory.
It does not accept paths or write any home-directory files. No authentication,
account listing or secret reads run during installation/lifecycle/shell startup.

## Installation and trust

Installs the latest official signed apt CLI, Python 3, sudo, curl, GnuPG and CA
certificates. CLI ownership is root/configured numeric GID, mode 2755.
No host accounts, sessions or settings are copied. Mise or other PATH shims must
not shadow `/usr/bin/op`; no wrapper or dotfiles modification is installed.

Trust the container: socket access is not per-secret isolation, and ordinary
container root can manipulate numeric identities. Desktop authorization still
applies. No privileged mode, extra capabilities, host PID/network sharing, or
broad runtime-directory mounts are requested.

Feature-owned installation files:

- `/usr/local/share/1password-desktop/`: root-owned helper and configuration.
- `/usr/local/bin/1password-desktop-doctor`.
- `/etc/sudoers.d/1password-desktop`: exact fixed-user runtime helper only.
- Official apt keyrings, source and signature policy.

The Feature may initialize the canonical socket-only runtime directory as
specified above. Existing 1Password user configuration is neither read nor changed.

## Diagnostics, recovery and rollback

Run `1password-desktop-doctor` as the remote user. It checks user identity, PATH,
CLI permissions, runtime compatibility/ownership, socket UID, integration toggle,
NoNewPrivs and the CLI filesystem's nosuid flag. It never authenticates, dumps
settings or reads account/secret data. These checks do not prove authorization.

App restart may replace the socket inode, leaving a single-file bind mount stale.
Recreate the container to recover; restarting it may retain the stale mount.
Rollback: remove the Feature reference and rebuild. This design creates no user
settings requiring cleanup. Any settings previously created by 0.1.0 are left
untouched; remove only its boolean manually if rolling back that older version.

## Personal additional Features and project lockfiles

Keep project lockfile handling enabled. Published additional Features are excluded
from generated project lockfile entries. With bundled CLI 0.89.0, a valid non-empty
project lockfile remained byte-identical and a frozen-lockfile build succeeded.
An unlocked project still gained an empty `features` lockfile. A Feature cannot
prevent this engine-level write through metadata; prefer a client fix over global
disabling or lifecycle deletion of project files.

Source: reference CLI [lockfile generation/writing](https://github.com/devcontainers/cli/blob/d807cb27c195b6bc0e89d893fc20f44a30bf27ee/src/spec-configuration/lockfile.ts#L16-L85).

## Validation and sources

0.2.0 passed the four-image no-socket matrix and bundled-CLI Dockerfile/Compose
socket/UID/lifecycle/diagnostic tests. Those fixtures preserved unset (Dockerfile)
or canonical (Compose) XDG_RUNTIME_DIR and created no user settings. Desktop sign-in under the new layout remains
an explicit pending check. Cache expiry and end-to-end secret reads are untested.

Official [environment reference](https://www.1password.dev/cli/environment-variables.md),
[app integration](https://www.1password.dev/cli/app-integration.md),
[Linux integration security](https://www.1password.dev/cli/app-integration-security.md),
and [XDG runtime requirements](https://specifications.freedesktop.org/basedir-spec/latest/).
The canonical socket filename/fallback is observed behavior of CLI 2.41.1, not a
published vendor guarantee of container support.
