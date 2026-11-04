#!/usr/bin/env python3
"""Build the ten top-starred static Skill packages as deterministic .orax files."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog.toml"
ASSET_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def git() -> str:
    """Return the git executable, allowing a Windows git override in local builds."""
    return os.environ.get("GIT_BIN", "git")


def run(*command: str, cwd: Path | None = None) -> str:
    """Run a command and return stdout, surfacing stderr on failure."""
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise ValueError(f"{' '.join(command)} failed: {message}")
    return result.stdout


def toml_string(value: str) -> str:
    """Encode a string as a TOML basic string."""
    return json.dumps(value, ensure_ascii=False)


def read_frontmatter_name(skill_md: Path) -> str:
    """Read and validate the scalar name from a SKILL.md front matter block."""
    raw = skill_md.read_text(encoding="utf-8")
    if len(raw.encode("utf-8")) > 1024 * 1024 or not raw.startswith("---\n"):
        raise ValueError(f"{skill_md}: missing or oversized front matter")
    end = raw.find("\n---", 4)
    if end < 0:
        raise ValueError(f"{skill_md}: unterminated front matter")
    header = raw[4:end]
    match = re.search(r"^name\s*:\s*(.+?)\s*$", header, re.MULTILINE)
    if match is None:
        raise ValueError(f"{skill_md}: front matter has no name")
    value = match.group(1).strip()
    if value[:1] in {'"', "'"} and value[-1:] == value[:1]:
        value = value[1:-1]
    if not ASSET_NAME.fullmatch(value):
        raise ValueError(f"{skill_md}: invalid skill name {value!r}")
    return value


def validate_tree(path: Path) -> None:
    """Reject symlinks and special files before they enter an archive."""
    for entry in path.rglob("*"):
        if entry.is_symlink():
            raise ValueError(f"symlink is not allowed in a skill package: {entry}")
        if not entry.is_file() and not entry.is_dir():
            raise ValueError(f"unsupported file type in a skill package: {entry}")


def fetch_repository(package: dict, checkout: Path) -> None:
    """Check out the pinned upstream commit into an empty directory."""
    checkout.mkdir(parents=True)
    run(git(), "init", "-q", cwd=checkout)
    run(git(), "config", "core.autocrlf", "false", cwd=checkout)
    run(git(), "remote", "add", "origin", f"https://github.com/{package['repository']}.git", cwd=checkout)
    run(git(), "fetch", "--depth=1", "origin", package["commit"], cwd=checkout)
    run(git(), "checkout", "-q", "--detach", "FETCH_HEAD", cwd=checkout)
    actual = run(git(), "rev-parse", "HEAD", cwd=checkout).strip()
    if actual != package["commit"]:
        raise ValueError(f"{package['repository']}: checked out {actual}, expected {package['commit']}")


def copy_license_files(package: dict, checkout: Path, stage: Path) -> None:
    """Copy every declared upstream license file with a clear package name."""
    for relative in package["license_files"]:
        source = checkout / relative
        if not source.is_file():
            raise ValueError(f"{package['repository']}: missing license file {relative}")
        name = "UPSTREAM_" + relative.replace("/", "-")
        shutil.copyfile(source, stage / name)


def package_manifest(package: dict) -> str:
    """Render the installed-form manifest for one package."""
    return "\n".join(
        [
            "resolver = 1",
            f"title = {toml_string(package['title'])}",
            f"identifier = {toml_string(package['identifier'])}",
            f"namespace = {toml_string(package['namespace'])}",
            'kind = "skill"',
            f"version = {toml_string(package['version'])}",
            f"description = {toml_string(package['description'])}",
            f"homepage = {toml_string(package['homepage'])}",
            f"license = {toml_string(package['license'])}",
            "",
        ]
    )


def package_readme(package: dict, skill_name: str) -> str:
    """Render the attribution document shipped inside the archive."""
    return f"""# {package["title"]}

{package["description"]}

This static Ora Skill plugin contains the `{skill_name}` skill from
[{package["repository"]}]({package["homepage"]}).

## Source

- Repository: `{package["repository"]}`
- Commit: `{package["commit"]}`
- Skill path: `{package["skill_path"]}`
- Stars snapshot: {package["stars"]} on 2026-11-04
- License: {package["license"]}

The upstream license text is included as `UPSTREAM_*`; `SOURCE.json` records
the exact provenance used by the deterministic build.
"""


def source_record(package: dict, skill_name: str) -> str:
    """Render stable machine-readable provenance."""
    return json.dumps(
        {
            "author": package["author"],
            "commit": package["commit"],
            "license": package["license"],
            "repository": package["repository"],
            "skill": skill_name,
            "skill_path": package["skill_path"],
            "snapshot_date": package["snapshot_date"],
            "stars": package["stars"],
            "excluded_paths": package.get("exclude", []),
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def prune_skill(root: Path, patterns: list[str]) -> None:
    """Remove explicitly excluded upstream files without leaving empty directories."""
    if not patterns:
        return
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if relative in {"SKILL.md", "LICENSE"}:
                continue
            if any(fnmatch.fnmatchcase(relative, pattern) for pattern in patterns):
                path.unlink()
        elif path != root and not any(path.iterdir()):
            path.rmdir()
    if not (root / "SKILL.md").is_file():
        raise ValueError(f"pruning removed SKILL.md from {root}")


def stage_package(package: dict, checkout: Path, stage: Path) -> str:
    """Copy the selected upstream skill and provenance into a package root."""
    source = checkout / package["skill_path"]
    if not source.is_dir():
        raise ValueError(f"{package['repository']}: skill directory is missing: {package['skill_path']}")
    asset_name = package.get("asset_name", source.name)
    skill_md = source / "SKILL.md"
    if not skill_md.is_file():
        raise ValueError(f"{package['repository']}: selected skill has no SKILL.md")
    skill_name = read_frontmatter_name(skill_md)
    if skill_name.lower() != asset_name.lower():
        raise ValueError(
            f"{package['repository']}: SKILL.md name {skill_name!r} does not match asset {asset_name!r}"
        )

    assets = stage / "assets"
    assets.mkdir(parents=True)
    copied = assets / asset_name
    shutil.copytree(source, copied, symlinks=False, ignore=shutil.ignore_patterns(".git"))
    prune_skill(copied, package.get("exclude", []))
    validate_tree(copied)
    (stage / "orax.toml").write_text(package_manifest(package), encoding="utf-8", newline="\n")
    (stage / "README.md").write_text(package_readme(package, skill_name), encoding="utf-8", newline="\n")
    (stage / "SOURCE.json").write_text(source_record(package, skill_name), encoding="utf-8", newline="\n")
    copy_license_files(package, checkout, stage)
    return skill_name


def validate_stage(package: dict, stage: Path, skill_name: str) -> None:
    """Validate the installed-form package before deterministic archiving."""
    manifest = tomllib.loads((stage / "orax.toml").read_text(encoding="utf-8"))
    expected = {
        "resolver": 1,
        "kind": "skill",
        "identifier": package["identifier"],
        "namespace": package["namespace"],
        "version": package["version"],
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"{package['identifier']}: manifest {key} is {manifest.get(key)!r}, expected {value!r}")
    if (stage / "main.js").exists():
        raise ValueError(f"{package['identifier']}: static Skill plugin must not ship main.js")
    entries = sorted((stage / "assets").iterdir(), key=lambda path: path.name)
    if len(entries) != 1 or not entries[0].is_dir() or entries[0].name != skill_name:
        raise ValueError(f"{package['identifier']}: assets must contain exactly {skill_name!r}")
    if not (entries[0] / "SKILL.md").is_file():
        raise ValueError(f"{package['identifier']}: assets/{skill_name}/SKILL.md is missing")


def archive_entries(stage: Path) -> list[tuple[Path, str]]:
    """Return sorted (source, archive name) pairs."""
    return [
        (path, path.relative_to(stage).as_posix())
        for path in sorted(stage.rglob("*"))
        if path.is_file()
    ]


def build_archive(package: dict, stage: Path, output: Path) -> tuple[Path, str]:
    """Write a deterministic ZIP-format .orax and return its path and digest."""
    archive_path = output / f"{package['identifier']}-{package['version']}.orax"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source, arcname in sorted(archive_entries(stage), key=lambda entry: entry[1]):
            info = zipfile.ZipInfo(arcname, date_time=FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            archive.writestr(info, source.read_bytes())
    return archive_path, hashlib.sha256(archive_path.read_bytes()).hexdigest()


def registry_entry(package: dict, digest: str, url_base: str) -> str:
    """Render a marketplace release-form manifest."""
    archive_name = f"{package['identifier']}-{package['version']}.orax"
    return package_manifest(package).rstrip() + "\n\n" + "\n".join(
        [
            f"url = {toml_string(url_base.rstrip('/') + '/' + archive_name)}",
            f"sha256 = {toml_string(digest)}",
            "",
        ]
    )


def write_registry(package: dict, skill_name: str, digest: str, registry_root: Path, url_base: str) -> None:
    """Write one registry listing and its README."""
    directory = registry_root / package["identifier"]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "orax.toml").write_text(
        registry_entry(package, digest, url_base), encoding="utf-8", newline="\n"
    )
    (directory / "README.md").write_text(
        package_readme(package, skill_name), encoding="utf-8", newline="\n"
    )


def load_catalog() -> list[dict]:
    """Load and complete catalog entries."""
    catalog = tomllib.loads(CATALOG.read_text(encoding="utf-8"))
    packages = catalog.get("packages")
    if not isinstance(packages, list) or len(packages) != 10:
        raise ValueError("catalog.toml must contain exactly ten [[packages]] entries")
    seen = set()
    result = []
    for package in packages:
        completed = dict(package)
        completed["namespace"] = catalog["namespace"]
        completed["snapshot_date"] = catalog["snapshot_date"]
        identifier = completed["identifier"]
        if identifier in seen:
            raise ValueError(f"duplicate identifier: {identifier}")
        seen.add(identifier)
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*(?:\.[a-z0-9][a-z0-9-]*)?", identifier):
            raise ValueError(f"invalid identifier: {identifier}")
        result.append(completed)
    return result


def build_all(packages: list[dict], output: Path) -> list[tuple[dict, str, Path, str]]:
    """Build all archives in an isolated checkout."""
    output.mkdir(parents=True, exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory(prefix="ora-top-skills-") as temporary:
        temp = Path(temporary)
        for package in packages:
            checkout = temp / package["slug"] / "repo"
            stage = temp / package["slug"] / "stage"
            fetch_repository(package, checkout)
            stage.mkdir(parents=True)
            skill_name = stage_package(package, checkout, stage)
            validate_stage(package, stage, skill_name)
            archive_path, digest = build_archive(package, stage, output)
            results.append((package, skill_name, archive_path, digest))
            print(f"{archive_path.name}  sha256={digest}")
    return results


def archive_skill_names(archive_bytes: bytes) -> set[str]:
    """Return the canonical Skill names contributed by one package archive."""
    names = set()
    with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
        for entry in archive.infolist():
            parts = entry.filename.split("/")
            if len(parts) != 3 or parts[0] != "assets" or parts[2] != "SKILL.md":
                continue
            content = archive.read(entry)
            raw = content.decode("utf-8")
            if not raw.startswith("---\n"):
                raise ValueError(f"{entry.filename}: missing front matter")
            end = raw.find("\n---", 4)
            if end < 0:
                raise ValueError(f"{entry.filename}: unterminated front matter")
            match = re.search(r"^name\s*:\s*(.+?)\s*$", raw[4:end], re.MULTILINE)
            if match is None:
                raise ValueError(f"{entry.filename}: front matter has no name")
            name = match.group(1).strip().strip('"\'')
            if not ASSET_NAME.fullmatch(name):
                raise ValueError(f"{entry.filename}: invalid Skill name {name!r}")
            names.add(name.lower())
    if not names:
        raise ValueError("package archive has no direct assets/<skill>/SKILL.md entries")
    return names


def existing_skill_names(registry_root: Path) -> dict[str, str]:
    """Read Skill names from published registry packages other than this batch."""
    existing: dict[str, str] = {}
    for manifest_path in sorted(registry_root.rglob("orax.toml")):
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        identifier = manifest.get("identifier")
        if manifest.get("kind") != "skill" or not isinstance(identifier, str) or identifier.startswith("top-skills."):
            continue
        locator = manifest.get("url")
        digest = manifest.get("sha256")
        if not isinstance(locator, str) or not isinstance(digest, str):
            targets = manifest.get("targets")
            if isinstance(targets, list) and targets:
                locator, digest = targets[0].get("url"), targets[0].get("sha256")
            else:
                continue
        with urllib.request.urlopen(locator, timeout=60) as response:
            payload = response.read()
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ValueError(f"{manifest_path}: downloaded Skill archive digest does not match {digest}")
        for name in archive_skill_names(payload):
            if name in existing:
                raise ValueError(
                    f"existing registry already has duplicate Skill {name!r}: "
                    f"{existing[name]} and {identifier}"
                )
            existing[name] = identifier
    return existing


def assert_no_duplicate_skills(
    results: list[tuple[dict, str, Path, str]], registry_root: Path
) -> None:
    """Refuse packages whose Skill names collide within the batch or with existing registry."""
    published = existing_skill_names(registry_root)
    current: dict[str, str] = {}
    for package, skill_name, _archive_path, _digest in results:
        canonical = skill_name.lower()
        identifier = package["identifier"]
        if canonical in published:
            raise ValueError(
                f"{identifier}: Skill {skill_name!r} duplicates existing package {published[canonical]}"
            )
        if canonical in current:
            raise ValueError(
                f"{identifier}: Skill {skill_name!r} duplicates package {current[canonical]}"
            )
        current[canonical] = identifier


def check_all(packages: list[dict], results: list[tuple[dict, str, Path, str]], registry_root: Path) -> None:
    """Verify committed archive bytes and registry digests."""
    for package, _skill_name, archive_path, digest in results:
        committed = ROOT / "dist" / archive_path.name
        if not committed.is_file():
            raise ValueError(f"committed archive is missing: {committed}")
        actual = hashlib.sha256(committed.read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError(f"archive is stale: {committed} ({actual} != {digest})")
        listing = registry_root / "t" / package["identifier"] / "orax.toml"
        if not listing.is_file():
            raise ValueError(f"registry listing is missing: {listing}")
        release = tomllib.loads(listing.read_text(encoding="utf-8"))
        if release.get("sha256") != digest:
            raise ValueError(f"registry digest is stale: {listing}")
        url = release.get("url")
        if not isinstance(url, str) or not url.endswith("/" + archive_path.name):
            raise ValueError(f"registry URL does not name the archive: {listing}")
        if not url.startswith("https://"):
            raise ValueError(f"registry URL is not HTTPS: {listing}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    parser.add_argument("--registry-root", type=Path, default=ROOT.parents[1] / "registry")
    parser.add_argument("--write-registry", action="store_true")
    parser.add_argument("--registry-base")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.write_registry and not args.registry_base:
        parser.error("--write-registry requires --registry-base")
    if args.registry_base and not args.registry_base.startswith("https://"):
        parser.error("--registry-base must be HTTPS")

    packages = load_catalog()
    results = build_all(packages, args.out)
    if args.write_registry or args.check:
        assert_no_duplicate_skills(results, args.registry_root)
    if args.write_registry:
        for package, skill_name, _archive_path, digest in results:
            write_registry(package, skill_name, digest, args.registry_root / "t", args.registry_base)
    if args.check:
        check_all(packages, results, args.registry_root)
        print(f"verified {len(results)} packages")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, tomllib.TOMLDecodeError, zipfile.BadZipFile) as error:
        print(f"top-skills build failed: {error}", file=sys.stderr)
        raise SystemExit(1)
