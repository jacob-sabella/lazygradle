#!/usr/bin/env bash
# Release validation gate. Run before tagging a new version, or wire it
# into CI so a red run blocks the PyPI publish.
#
# Steps (in order):
#   1. pytest          — full functional suite against the fixture project
#   2. pip-audit       — known PyPA advisories on declared dependencies
#   3. python -m build — sdist + wheel
#   4. twine check     — long-description renders cleanly on PyPI
#
# Exits non-zero on the first failure. Run from repo root. README screenshots
# are a documentation concern (scripts/capture_readme_screenshots.py), not a
# release gate, so they are intentionally not regenerated here.

set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> pytest"
python -m pytest

echo "==> pip-audit"
python -m pip_audit -r requirements.txt --strict

echo "==> python -m build"
rm -rf dist
python -m build

echo "==> twine check"
python -m twine check dist/*

echo
echo "release-check: PASS"
