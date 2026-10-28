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

### Lockfiles

Actual isolated VS Code User defaultFeatures injection passed for Dockerfile
and Compose. Further published-artifact tests with bundled CLI 0.89.0 found:

| Project state | Normal lockfile handling plus this additional Feature |
| --- | --- |
| No existing lockfile | Creates an empty `features` lockfile: a project-file change |
| Valid non-empty project lockfile | Preserves exact bytes; frozen-lockfile build succeeds |

Personal additional Features are deliberately excluded from generated lockfile
entries. Thus globally disabling lockfile handling is **not necessary** for an
already locked project and would unnecessarily disable project verification.
The remaining no-project-edits issue is empty lockfile creation in unlocked
projects. A Feature cannot prevent the engine's lockfile write through its own
metadata. Prefer an upstream client fix over deleting project files from a
lifecycle hook or globally disabling lockfiles.

Source: reference CLI [lockfile generation/writing](https://github.com/devcontainers/cli/blob/d807cb27c195b6bc0e89d893fc20f44a30bf27ee/src/spec-configuration/lockfile.ts#L16-L85).
The bundled 0.89.0 implementation was also inspected and tested directly.

### Runtime environment

Version 0.1.0's global runtime override can affect D-Bus, Wayland, audio and other
tools. Disposable fake-socket probes with official CLI 2.41.1 on Ubuntu 24.04
showed that it attempts `/run/user/<uid>/1Password-BrowserSupport.sock` when
`XDG_RUNTIME_DIR` is unset, and uses the configured runtime path when set.
This tests endpoint selection, **not successful desktop authentication**.

A prospective replacement can mirror only the host socket's canonical path and
leave `XDG_RUNTIME_DIR` untouched, provided the container's existing runtime
(or the unset-variable fallback) resolves to that same path. A different working
container runtime requires an explicit policy; do not silently override it or
mount the whole host runtime directory. Host-path mirroring through `localEnv`
does not itself discover an arbitrary container runtime. This replacement is
not implemented or released yet.

No desktop socket-path override is documented in the official CLI
[environment reference](https://www.1password.dev/cli/environment-variables.md).
`OP_BIOMETRIC_UNLOCK_ENABLED=true` is a documented integration toggle, not a
socket override. A fake-socket probe connected with this toggle and no settings
file; whether it can replace settings mutation needs real integration validation.

An explicit `env XDG_RUNTIME_DIR=/run/1password-desktop /usr/bin/op ...` invocation
avoids changing unrelated processes, but needs consumer cooperation and passes
the changed runtime to children of `op run`. It is not a transparent solution
for tools that invoke plain `op` themselves. Do not shadow the genuine CLI.

See official [app integration](https://www.1password.dev/cli/app-integration.md),
[Linux integration security](https://www.1password.dev/cli/app-integration-security.md),
and [XDG runtime requirements](https://specifications.freedesktop.org/basedir-spec/latest/).
Cache reuse/expiry and end-to-end secret retrieval remain unverified; no test
secret reads have been performed.
