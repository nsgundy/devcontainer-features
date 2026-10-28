# Tests

## Automated distro/security matrix

```sh
python3 test/1password-desktop/run_matrix.py
```

Defaults to Debian 12/13 and Ubuntu 22.04/24.04; pass image references to select a
subset. Each image runs 15 runtime tests and 9 container tests (96 executions).
Installation runs twice. Builds use distro and official 1Password apt repositories;
runtime tests use `--network none`, no host mounts, credentials or desktop app.
Fake socket fixtures test metadata/ownership only; no protocol is implemented.
Tagged test images are removed; build cache/base images may remain.

Coverage: CLI permissions, GID validation/collisions, lifecycle reruns, canonical
runtime compatibility, root/socket-only initialization, existing runtime
preservation, parent/runtime/socket symlinks, foreign ownership, unsafe modes,
missing socket/runtime, PATH shadowing, NoNewPrivs, restricted sudo invocation,
and byte/owner/mode preservation of pre-existing malformed user settings.

The two pure environment-policy tests can run without Docker:

```sh
python3 test/1password-desktop/test_runtime.py
```

Root-only filesystem cases are skipped there and run in disposable containers.

## Explicit local socket integration

```sh
python3 test/1password-desktop/test_devcontainers.py \
  --allow-desktop-access --no-lockfile --cli /path/to/devContainersSpecCLI.js
```

Uses disposable Dockerfile and Compose fixtures and additional Features. Checks
socket mount substitution, UID remapping, postStart setup, doctor output,
idempotency, preservation of unset (Dockerfile) or canonical (Compose)
XDG_RUNTIME_DIR, absent user settings creation,
and before/after workspace hashes. No authentication or secret reads by default.
Containers, Compose networks, fixtures and tagged images are cleaned up.

An optional `--check-desktop-signin` explicitly attempts sign-in and may prompt on
the desktop. All raw CLI output is suppressed; only a success boolean is printed.
No vault items are read. This flag is never used in CI. The revised runtime layout
has passed diagnostics but sign-in remains pending operator-coordinated validation.

`--no-lockfile` is used only to isolate the runtime tests from known client-level
empty lockfile generation; it is not a recommendation for normal User settings.

## Lockfile behavior

Separate published-0.1.0 builds with bundled CLI 0.89.0 confirmed:

- No existing lockfile: an empty `features` lockfile is created.
- Existing non-empty lockfile for the project git Feature: injecting a personal
  Feature leaves bytes unchanged and passes `--frozen-lockfile`.
- The personal Feature is not recorded in the project lockfile.

These builds used a clean HOME/Docker config and no desktop socket. Additional
Feature exclusion is client behavior, independent of the runtime redesign.

## Legacy artifact smoke test

`test_public_artifact.py --cli /path/to/devContainersSpecCLI.js` targets immutable
published 0.1.0: anonymous tag/digest retrieval, layer integrity, released file
allowlist/metadata, and installation with fresh HOME and empty credential config.
It does not test 0.2.0 and will cease to work if the legacy package is withdrawn.
A replacement published-artifact check is required before releasing 0.2.0.
