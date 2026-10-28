# Dev Container Features

Experimental native-Linux 1Password desktop integration for trusted devcontainers.

## Feature

- [1password-desktop](src/1password-desktop/README.md)
- Published reference: `ghcr.io/nsgundy/devcontainer-features/1password-desktop:0.1.0`
- License: [MIT](LICENSE)

Supports Debian/Ubuntu containers on native Linux with rootful Docker, no user
namespace remapping, and matching host/container UID. It installs the official
CLI and mounts only the desktop integration socket. No authentication or secret
reads run automatically.

**Before adoption:** version 0.1.0 globally overrides container `XDG_RUNTIME_DIR`.
Lockfile behavior for personal default Features also needs care. See the Feature
README; do not disable lockfile verification globally without understanding the
impact on other projects. Main-branch documentation may evolve independently
of the immutable published package.

## Tests and publishing

See [test instructions](test/1password-desktop/README.md). Automated tests need
Docker but no desktop app or credentials. Real socket integration is opt-in.

CI tests Debian 12/13 and Ubuntu 22.04/24.04. A manually triggered release workflow
runs the same matrix before publishing from `main`. Third-party Actions are
SHA-pinned. Publishing uses `GITHUB_TOKEN` with contents read and packages write;
no documentation PR or repository tag generation is enabled.

## Initial release

Version: `0.1.0`

Manifest digest:
`sha256:6657a917a6ce58e346e920155939a49fbee6a203a2f07914fd6ddc1fb47f711a`

Tags `0.1.0`, `0.1`, `0`, and `latest` were verified at initial publication.
Prefer the exact version for initial validation. Anonymous retrieval and
credential-free installation passed. Personal VS Code settings, dotfiles and
existing project containers are never modified by publishing this Feature.
