#!/usr/bin/env python3
"""Read, set, or bump the ``[project]`` version in ``pyproject.toml``.

This is the single source of truth for the release version. CI writes the
concrete release version here just before ``python -m build`` so that the git
tag, the GitHub release, and the published PyPI artifact always carry the same
PEP 440 string. Only stdlib is used so the script runs anywhere.

Usage:
    set-version.py --get            # print current version (e.g. 1.3.0)
    set-version.py --base           # print release segment only (X.Y.Z)
    set-version.py --bump minor     # print the next base (does not write)
    set-version.py 1.3.0b7          # write an explicit PEP 440 version
"""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"

# The only `version = "..."` line in pyproject.toml belongs to [project]
# ([build-system] declares no version), so matching the first one is safe.
_VERSION_LINE = re.compile(r'^version\s*=\s*"[^"]*"', re.MULTILINE)
_BASE = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?")


def read_version() -> str:
    """Return the version currently declared in pyproject.toml."""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return data["project"]["version"]


def base_of(version: str) -> tuple[int, int, int]:
    """Return the ``(major, minor, micro)`` release segment of a PEP 440 version."""
    match = _BASE.match(version)
    if not match:
        raise ValueError(f"cannot parse a release segment from {version!r}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)


def bump(version: str, part: str) -> str:
    """Return the next base version after ``version`` for the given part."""
    major, minor, micro = base_of(version)
    if part == "major":
        major, minor, micro = major + 1, 0, 0
    elif part == "minor":
        minor, micro = minor + 1, 0
    elif part == "patch":
        micro += 1
    else:
        raise ValueError(f"unknown bump part: {part!r}")
    return f"{major}.{minor}.{micro}"


def write_version(version: str) -> None:
    """Rewrite the [project] version line in place, preserving everything else."""
    text = PYPROJECT.read_text(encoding="utf-8")
    new_text, count = _VERSION_LINE.subn(f'version = "{version}"', text, count=1)
    if count != 1:
        raise SystemExit("could not locate the [project] version line in pyproject.toml")
    PYPROJECT.write_text(new_text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--get", action="store_true", help="print the current version")
    group.add_argument("--base", action="store_true", help="print the X.Y.Z release segment")
    group.add_argument(
        "--bump", choices=("major", "minor", "patch"), help="print the next base version"
    )
    group.add_argument("version", nargs="?", help="explicit PEP 440 version to write")
    args = parser.parse_args(argv)

    current = read_version()
    if args.get:
        print(current)
    elif args.base:
        print("{}.{}.{}".format(*base_of(current)))
    elif args.bump:
        print(bump(current, args.bump))
    else:
        write_version(args.version)
        print(args.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
