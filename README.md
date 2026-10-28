# Dev Container Features

Experimental native-Linux 1Password desktop integration for trusted devcontainers.

- [Feature documentation](src/1password-desktop/README.md)
- [Tests](test/1password-desktop/README.md)
- License: [MIT](LICENSE)

## Current work

**0.2.0 is under development, not published.** It uses the official apt CLI and
single canonical socket mount without overriding XDG_RUNTIME_DIR or changing
user settings. Incompatible runtimes fail clearly rather than being overwritten.

Supports Debian/Ubuntu containers on native Linux with rootful Docker, no user
namespace remapping, and matching host/container UID. No authentication or secret
reads run automatically. Desktop sign-in for the revised design remains pending.

Published 0.1.0 uses the older global-runtime-override design; main-branch code
and documentation must not be interpreted as its behavior. Its withdrawal is a
separate operation from Git history cleanup and development of the replacement.

Personal additional Features preserve a valid existing project lockfile, but the
client creates an empty lockfile for an unlocked project. Do not globally disable
lockfile verification as a blanket workaround.

## Testing and publishing

CI tests Debian 12/13 and Ubuntu 22.04/24.04 with no desktop credentials or host
socket. Local socket tests are opt-in. A manually triggered release workflow runs
the matrix before publishing from `main`. Third-party Actions are SHA-pinned.
Publishing uses GITHUB_TOKEN with contents read and packages write, without
documentation PRs or repository tag generation. Development commits do not publish.

Personal VS Code settings, dotfiles and existing project containers are never
modified by publishing or running automated tests.
