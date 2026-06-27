# Releasing LazyGradle

LazyGradle ships on two PyPI channels that share one project history, separated
only by [PEP 440](https://peps.python.org/pep-0440/) version semantics — PyPI has
no notion of channels, so the version string *is* the channel.

| Channel | Example version | How it's cut | Who gets it |
| --- | --- | --- | --- |
| **Beta** | `1.3.0b412` | Automatically, on every merge to `main` | `pip install --pre lazygradle` (or pinning) |
| **Stable** | `1.3.0` | Manually, via the **Stable Release** workflow | `pip install lazygradle` |

`pip install lazygradle` always resolves to the latest **final** version and
silently skips pre-releases, so betas never reach normal users.

## Single source of truth

`pyproject.toml` `version` holds the **next target final version** (e.g. `1.3.0`).
Everything else is derived from it by `scripts/set-version.py`, which CI writes
into `pyproject.toml` immediately before each build so the git tag, the GitHub
release, and the PyPI artifact always carry the same string.

## Beta channel — automatic

`.github/workflows/release-beta.yml` runs on every push to `main`
(code changes only — docs/screenshots/workflow edits are ignored):

1. **Validate** — reuses `release-check.yml` (pytest, pip-audit, build, twine).
2. **Publish** — computes `<base>b<run_number>` (e.g. `1.3.0b412`), creates a
   tag + GitHub pre-release, which triggers `python-publish.yml` → PyPI.

This is what makes the pipeline Dependabot-friendly: each weekly batch of grouped
dependency PRs lands a tested beta on its own, so dependency bumps soak on the
beta channel before they ever reach a stable user.

## Stable channel — deliberate

When a beta line is ready to ship, run the **Stable Release** workflow from the
Actions tab (`.github/workflows/release-stable.yml`):

1. **Validate** — the same `release-check.yml` gate.
2. **Release** — tags the current base as a final `vX.Y.Z`, publishes a GitHub
   release with auto-generated notes (which lists every PR — including Dependabot
   — since the last release), and triggers `python-publish.yml` → PyPI.
3. **Bump** — opens a PR setting `pyproject.toml` to the next development base
   (`patch` by default; choose `minor`/`major` via the workflow input). Merging
   it starts the next beta line.

To cut a `minor`/`major` release, first merge a PR bumping the base in
`pyproject.toml`, then run the Stable Release workflow.

## Requirements

- **`RELEASE_TOKEN`** (repo secret): a PAT used to create releases/tags. Required
  so the `release: published` event actually triggers `python-publish.yml` — the
  default `GITHUB_TOKEN` would not.
- **`pypi`** environment with [Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
  configured for `python-publish.yml`. Add a manual approval rule to this
  environment if you want a human to confirm every PyPI upload.

## Switching betas to TestPyPI (optional)

If you'd rather keep real PyPI final-only, point the publish step at
[TestPyPI](https://test.pypi.org) for pre-releases by adding
`repository-url: https://test.pypi.org/legacy/` to the
`pypa/gh-action-pypi-publish` step in `python-publish.yml`, guarded by
`github.event.release.prerelease`.
