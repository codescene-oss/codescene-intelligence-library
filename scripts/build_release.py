#!/usr/bin/env python3
"""Builds the release zip that clients download: only the files they need, with a manifest of hashes.

    python scripts/build_release.py                  # build from HEAD into dist/
    python scripts/build_release.py --tag v1.2.0     # also stop if the tag isn't the catalog's version

Runs no checks: pull requests validate everything before it reaches main. The files come from the commit,
not the working tree, so the same commit always builds the same zip, byte for byte.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

NAME = "codescene-intelligence-library"
# What clients need. Tooling, docs and schemas stay in the repo.
SHIPPED = ["catalog.json", "LICENSE", "shared", "skills"]
MANIFEST = "MANIFEST.json"
# Zip entries need a timestamp; a fixed one keeps the build reproducible.
FIXED_DATE = (1980, 1, 1, 0, 0, 0)


def git(root, *args):
    """Runs git in the repo and returns its raw output."""
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True).stdout


def shipped_files(root, commit):
    """Every tracked file a release ships, as committed, sorted by path."""
    out = git(root, "ls-tree", "-r", "--name-only", "-z", commit, "--", *SHIPPED)
    return sorted(p for p in out.decode("utf-8").split("\0") if p)


def read_committed(root, commit, path):
    """A file's content in the commit, so uncommitted edits never reach a release."""
    return git(root, "show", f"{commit}:{path}")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def manifest(version, commit, contents):
    """The manifest clients check synced files against: the sha256 of every other file in the zip."""
    files = {path: sha256(data) for path, data in contents.items()}
    return {"name": NAME, "version": version, "commit": commit, "files": files}


def zip_entry(path):
    """A zip entry with a fixed date and permissions, so nothing about the build machine leaks in."""
    info = zipfile.ZipInfo(path, date_time=FIXED_DATE)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info


def write_zip(path, contents):
    """Writes the files at the zip's root, in path order."""
    with zipfile.ZipFile(path, "w") as archive:
        for name in sorted(contents):
            archive.writestr(zip_entry(name), contents[name])


def build(root, out_dir, tag=None):
    """Builds the zip and its .sha256 from HEAD and returns the zip's path.

    Raises ValueError when the tag doesn't name the catalog's version: a published release can't be renamed.
    """
    root = Path(root).resolve()
    commit = git(root, "rev-parse", "HEAD").decode().strip()
    contents = {path: read_committed(root, commit, path) for path in shipped_files(root, commit)}
    version = json.loads(contents["catalog.json"])["version"]
    if tag is not None and tag != f"v{version}":
        raise ValueError(f'tag {tag} doesn\'t match catalog.json version "{version}"; tag v{version} instead')
    contents[MANIFEST] = (json.dumps(manifest(version, commit, contents), indent=2) + "\n").encode()

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{NAME}-{version}.zip"
    write_zip(zip_path, contents)
    # The format sha256sum and shasum read, so `shasum -a 256 -c` verifies a download.
    Path(f"{zip_path}.sha256").write_text(f"{sha256(zip_path.read_bytes())}  {zip_path.name}\n")
    return zip_path


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", help="the release tag; the build stops unless it is v<catalog version>")
    parser.add_argument("--out", default="dist", help="where to write the zip and its .sha256 (default: dist)")
    parser.add_argument("--root", default=Path(__file__).resolve().parent.parent, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        zip_path = build(args.root, args.out, args.tag)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    print(zip_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
