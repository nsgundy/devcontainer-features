# Creating a release

1. Update `version` in `src/1password-desktop/devcontainer-feature.json` to a new
   stable version (for example `0.2.2`, without a `v` prefix).
2. Add `releases/0.2.2.md` with the release notes. Do not copy digest or install
   boilerplate: the workflow adds the verified artifact reference automatically.
3. Commit and push to `main` using the repository's commit identity conventions.
4. Open **Actions → Release Features → Run workflow**, select `main`, and enter
   `0.2.2`. Alternatively, using a GitHub account authorized for the repository:

   ```sh
   gh workflow run release.yml --repo nsgundy/devcontainer-features \
     --ref main -f version=0.2.2
   ```

The workflow refuses mismatched metadata, missing notes, existing Git tags,
existing GitHub Releases and existing immutable package versions. Network/auth
errors fail closed. It runs the four-image matrix and release-policy tests, then
publishes both the Feature and its collection index. Before creating `v0.2.2`
and its GitHub Release at the exact workflow commit, it checks anonymous tag
retrieval, archive integrity/exact source contents, and installation with fresh
HOME and empty credential configuration. No desktop authentication or secret
reads run in CI.

Stable package aliases (`major.minor`, `major`, `latest`) move on publication;
explicit version tags are never intentionally overwritten. The collection index
is maintained automatically for discovery and future Features.

If publication succeeded but verification/release creation failed, investigate
and use **Re-run failed jobs** on that same workflow run. A fresh dispatch of
an already published version is intentionally refused. Do not delete/re-publish
an immutable version to repair missing GitHub Release metadata.

For checks of an older release, use its tagged checkout: the artifact test compares
the published payload to the source files in that checkout. Moving aliases may
already point to a later version, so the full alias check is a release-time gate.
