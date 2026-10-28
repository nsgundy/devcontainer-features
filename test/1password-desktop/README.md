# Tests

## Automated distro/security matrix

```sh
python3 test/1password-desktop/run_matrix.py
```

Defaults to Debian 12/13 and Ubuntu 22.04/24.04; pass image references as arguments
to select a subset. Each image runs 13 settings tests and 9 container tests.
Installation runs twice. Builds use distro and official 1Password apt repositories;
runtime tests use `--network none`, no host mounts, no credentials or desktop app.
Tagged test images are removed; build cache/base images may remain.

Coverage: CLI permissions, GID validation/collisions, lifecycle reruns, runtime
symlink rejection, settings preservation/mode repair, malformed and non-object
JSON, symlinks/hardlinks/FIFOs/foreign ownership, missing socket/runtime, PATH
shadowing, NoNewPrivs, and restricted sudo helper invocation.

Settings-only tests can run without Docker:

```sh
python3 test/1password-desktop/test_settings.py
```

Foreign-ownership cases run only as root in disposable matrix containers.

## Published artifact smoke test

```sh
python3 test/1password-desktop/test_public_artifact.py --cli /path/to/devContainersSpecCLI.js
```

Checks anonymous tag/digest retrieval, layer integrity, the released file
allowlist and metadata, then installs exact version 0.1.0 using fresh HOME,
empty Docker config and fresh CLI data without token environment variables.
No desktop socket is mounted. This targets the immutable published release,
not byte equality with evolving main-branch documentation.

## Explicit local socket integration

```sh
python3 test/1password-desktop/test_devcontainers.py \
  --allow-desktop-access --no-lockfile --cli /path/to/devContainersSpecCLI.js
```

Uses disposable Dockerfile and Compose fixtures and additional Features. Checks
socket mount substitution, UID remapping, postStart setup, doctor output,
idempotency and before/after workspace hashes. No authentication or secret reads.
Containers, Compose networks, fixtures and tagged images are cleaned up.

Without `--no-lockfile`, the local-Feature case creates a lockfile and deliberately
fails the no-project-modifications gate. This does not by itself establish the
behavior of a published OCI Feature with normal project lockfiles.

Operator-tested published Feature injection through isolated VS Code User settings
passed for both fixture types with lockfile handling disabled. Existing empty
lockfiles stayed byte-identical. Desktop authorization and stale-socket recovery
were separately tested: app restart replaced the socket; container recreation
restored sign-in. These observations do not constitute a complete security audit.
