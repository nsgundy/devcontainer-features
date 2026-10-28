# Dev Container Features

Experimental native-Linux 1Password desktop integration for trusted devcontainers.

- [Feature documentation](src/1password-desktop/README.md)
- [Tests](test/1password-desktop/README.md)
- License: [MIT](LICENSE)

## Current work

**Experimental 0.2.1.** It uses the official apt CLI and
single canonical socket mount without overriding XDG_RUNTIME_DIR or changing
user settings. Incompatible runtimes fail clearly rather than being overwritten.

Supports Debian/Ubuntu containers on native Linux with rootful Docker, no user
namespace remapping, and matching host/container UID. No authentication or secret
reads run automatically. Desktop sign-in passed in disposable Dockerfile and
Compose containers, without a setup-time settings mutation.

Legacy 0.1.0 used a global-runtime-override design and has been unpublished.
The immutable 0.2.0 remains available; 0.2.1 removes its optional diagnostic tool.

Personal additional Features preserve a valid existing project lockfile, but the
client creates an empty lockfile for an unlocked project. Do not globally disable
lockfile verification as a blanket workaround.

## Testing and publishing

CI tests Debian 12/13 and Ubuntu 22.04/24.04 with no desktop credentials or host
socket. Local socket tests are opt-in. [One manual release workflow](releases/README.md) validates the version, runs
the matrix, publishes the Feature and collection index, verifies the public
artifact, and creates its matching GitHub tag and Release. Third-party Actions
are SHA-pinned. Publishing uses packages write; a separate release job uses
contents write. No documentation PRs are generated. Development commits do not publish.

Personal VS Code settings, dotfiles and existing project containers are never
modified by publishing or running automated tests.
