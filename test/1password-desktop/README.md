# Tests

## Automated distro/security matrix

```sh
python3 test/1password-desktop/run_matrix.py
```

Defaults to Debian 12/13 and Ubuntu 22.04/24.04; pass image references to select a
subset. Each image runs 15 runtime tests and 8 container tests (92 executions).
Installation runs twice. Builds use distro and official 1Password apt repositories;
runtime tests use `--network none`, no host mounts, credentials or desktop app.
Fake socket fixtures test metadata/ownership only; no protocol is implemented.
Tagged test images are removed; build cache/base images may remain.

Coverage: CLI permissions, GID validation/collisions, lifecycle reruns, canonical
runtime compatibility, root/socket-only initialization, existing runtime
preservation, parent/runtime/socket symlinks, foreign ownership, unsafe modes,
missing sockets, packaged CLI selection/execution, diagnostic-command absence,
restricted sudo invocation, and byte/owner/mode preservation of pre-existing
malformed user settings. Eight separate release-policy tests run without Docker:

```sh
python3 -m unittest discover -s test -p test_release.py -v
```

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
socket mount substitution, UID remapping, postStart setup, packaged CLI execution,
idempotency, preservation of unset (Dockerfile) or canonical (Compose)
XDG_RUNTIME_DIR, absent user settings creation,
and before/after workspace hashes. No authentication or secret reads by default.
Containers, Compose networks, fixtures and tagged images are cleaned up.

An optional `--check-desktop-signin` explicitly attempts sign-in and may prompt on
the desktop. All raw CLI output is suppressed; only a success boolean is printed.
No vault items are read. This flag is never used in CI. The revised runtime layout
passed desktop sign-in in both Dockerfile and Compose fixtures. The authorization
timeout is two minutes per container.

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

## Published-artifact smoke test

```sh
python3 test/1password-desktop/test_public_artifact.py \
  --cli /path/to/devContainersSpecCLI.js --expected-digest sha256:RELEASE_DIGEST
```

Targets the version in the checked-out Feature metadata: anonymous tag/digest
retrieval, layer integrity, exact release-source
comparison, and installation with fresh HOME and empty credential config.
The build mounts no desktop socket and does not authenticate. Moving `0`/`latest`
are checked against the expected release digest at validation time. Without
`--expected-digest`, the workflow derives it from the immutable version tag,
compares all aliases, and verifies exact source bytes before accepting it.
`--digest-output /path/to/file` records the digest only after installation passes.
