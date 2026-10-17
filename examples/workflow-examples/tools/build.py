#!/usr/bin/env python3
"""Build the deterministic `.orax` archive for this workflow package.

The archive layout is the one the workflow package decision fixes: `orax.toml`
at the root and the direct `assets/workflows/*.json` documents. Building is
reproducible -- entries are sorted, timestamps are fixed and permissions are
normalized -- so the same source always produces the same SHA-256.

Usage:
    python3 tools/build.py [--out DIR] [--base-url URL]

With `--base-url`, the tool also writes `DIR/manifest.toml`, the release form of
the manifest with the download `url` and `sha256` a registry entry needs. The
base URL must be HTTPS; the file name is appended to it.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tomllib
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import workflow_documents, validate_package  # noqa: E402

# A fixed timestamp keeps the archive byte-identical across runs. 1980-01-01 is
# the earliest value the ZIP format can represent.
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def staged_entries(root: Path) -> list[tuple[Path, str]]:
    """Return (source, archive name) pairs for every file the package ships."""
    manifest = root / "orax.toml"
    if not manifest.is_file():
        raise FileNotFoundError(f"{manifest} is missing")
    entries = [(manifest, "orax.toml")]
    for document in workflow_documents(root, []):
        entries.append((document, document.relative_to(root).as_posix()))
    return entries


def build_package(root: Path, out_dir: Path) -> tuple[Path, str]:
    """Validate, write the archive, and return its path and SHA-256 digest."""
    problems = validate_package(root)
    if problems:
        raise ValueError(f"package is invalid ({len(problems)} problem(s)); run validate.py")

    manifest = tomllib.loads((root / "orax.toml").read_text(encoding="utf-8"))
    identifier = manifest["identifier"]
    version = manifest["version"]
    archive_name = f"{identifier}-{version}.orax"

    out_dir.mkdir(parents=True, exist_ok=True)
    archive_path = out_dir / archive_name
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source, arcname in sorted(staged_entries(root), key=lambda entry: entry[1]):
            info = zipfile.ZipInfo(arcname, date_time=FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3  # Unix, so the permission bits below are meaningful.
            info.external_attr = 0o644 << 16
            archive.writestr(info, source.read_bytes())

    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    return archive_path, digest


def write_release_manifest(root: Path, out_dir: Path, archive_name: str, digest: str, base_url: str) -> Path:
    """Write the release form: the package manifest plus download url and digest."""
    if not base_url.startswith("https://"):
        raise ValueError("--base-url must be an HTTPS URL")
    base = base_url.rstrip("/")
    source = (root / "orax.toml").read_text(encoding="utf-8").rstrip()
    target = out_dir / "manifest.toml"
    target.write_text(
        f'{source}\nurl = "{base}/{archive_name}"\nsha256 = "{digest}"\n',
        encoding="utf-8",
    )
    return target


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build the workflow example .orax package.")
    parser.add_argument("--package", default=str(PACKAGE_ROOT), help="package directory")
    parser.add_argument("--out", default=str(PACKAGE_ROOT / "dist"), help="output directory")
    parser.add_argument("--base-url", default=None, help="HTTPS base URL for the release manifest")
    args = parser.parse_args(argv)

    root = Path(args.package).resolve()
    out_dir = Path(args.out).resolve()
    try:
        archive_path, digest = build_package(root, out_dir)
        print(f"{archive_path}  sha256={digest}")
        if args.base_url:
            release = write_release_manifest(root, out_dir, archive_path.name, digest, args.base_url)
            print(f"{release}")
    except (FileNotFoundError, KeyError, ValueError, tomllib.TOMLDecodeError) as error:
        print(f"build failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
