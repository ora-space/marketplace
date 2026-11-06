#!/usr/bin/env python3
"""Build the ten real Hook packages as deterministic, target-specific .orax files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKCTL = ROOT / "hookctl"
CATALOG = ROOT / "catalog.toml"
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
TARGETS = {
    "aarch64-apple-darwin": ("darwin", "arm64", "hookctl"),
    "aarch64-unknown-linux-gnu": ("linux", "arm64", "hookctl"),
    "x86_64-apple-darwin": ("darwin", "amd64", "hookctl"),
    "x86_64-pc-windows-msvc": ("windows", "amd64", "hookctl.exe"),
    "x86_64-unknown-linux-gnu": ("linux", "amd64", "hookctl"),
}
SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$"
)


def git() -> str:
    """Return the git executable, allowing an override in local builds."""
    return os.environ.get("GIT_BIN", "git")


def go() -> str:
    """Return the Go executable, allowing an override in local builds."""
    return os.environ.get("GO_BIN", "go")


def run(*command: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    """Run a command and return stdout, surfacing bounded stderr on failure."""
    merged = {**os.environ, "GIT_TERMINAL_PROMPT": "0", **(env or {})}
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        env=merged,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise ValueError(f"{' '.join(command)} failed: {message}")
    return result.stdout


def toml_string(value: str) -> str:
    """Encode a string as a TOML basic string."""
    return json.dumps(value, ensure_ascii=False)


def fetch_repository(repository: str, commit: str, checkout: Path) -> None:
    """Check out one pinned upstream commit into an empty directory."""
    checkout.mkdir(parents=True)
    run(git(), "init", "-q", cwd=checkout)
    run(git(), "config", "core.autocrlf", "false", cwd=checkout)
    run(git(), "remote", "add", "origin", f"https://github.com/{repository}.git", cwd=checkout)
    run(git(), "fetch", "--depth=1", "origin", commit, cwd=checkout)
    run(git(), "checkout", "-q", "--detach", "FETCH_HEAD", cwd=checkout)
    actual = run(git(), "rev-parse", "HEAD", cwd=checkout).strip()
    if actual != commit:
        raise ValueError(f"{repository}: checked out {actual}, expected {commit}")


def validate_tree(path: Path) -> None:
    """Reject symlinks and special files before they enter an archive."""
    for entry in path.rglob("*"):
        if entry.is_symlink():
            raise ValueError(f"symlink is not allowed in a Hook package: {entry}")
        if not entry.is_file() and not entry.is_dir():
            raise ValueError(f"unsupported file type in a Hook package: {entry}")


def copy_selected(source: Path, destination: Path, includes: list[str] | None) -> None:
    """Copy a complete plugin directory or only its declared runtime subset."""
    destination.mkdir(parents=True)
    if includes is None:
        shutil.copytree(source, destination, symlinks=False, dirs_exist_ok=True)
        return
    for relative in includes:
        entry = source / relative
        if not entry.exists():
            raise ValueError(f"declared plugin runtime path is missing: {entry}")
        target = destination / relative
        if entry.is_dir():
            shutil.copytree(entry, target, symlinks=False)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(entry, target)


def load_json(path: Path) -> dict:
    """Read one UTF-8 JSON object."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    """Write stable two-space JSON with a trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def patched_hook_command(command: str, package: dict) -> str:
    """Apply only the dependency-pinning and Python fallback needed on Windows."""
    pinned = package.get("pin_npm_package")
    if pinned:
        command = command.replace("npx tdd-guard@latest", f"npx --yes {pinned}")
    if package.get("python_fallback") and command.startswith("python3 ") and " || " not in command:
        command = f"{command} || python {command[len('python3 '):]}"
    return command


def patch_hook_commands(plugin: Path, package: dict) -> None:
    """Pin runtime package versions and add a Windows Python fallback."""
    hooks_path = plugin / "hooks" / "hooks.json"
    if not hooks_path.is_file():
        return
    hooks = load_json(hooks_path)
    events = hooks.get("hooks")
    if not isinstance(events, dict):
        raise ValueError(f"{hooks_path}: hooks must be an object")
    for groups in events.values():
        if not isinstance(groups, list):
            raise ValueError(f"{hooks_path}: hook events must contain arrays")
        for group in groups:
            commands = group.get("hooks")
            if not isinstance(commands, list):
                raise ValueError(f"{hooks_path}: matcher groups must contain hooks")
            for command in commands:
                if command.get("type") == "command" and isinstance(command.get("command"), str):
                    command["command"] = patched_hook_command(command["command"], package)
    write_json(hooks_path, hooks)


def ensure_module_type(plugin: Path, package: dict) -> None:
    """Keep upstream CommonJS hooks independent of parent package metadata."""
    if not package.get("commonjs"):
        return
    manifest_path = plugin / "package.json"
    if manifest_path.exists():
        manifest = load_json(manifest_path)
        if manifest.get("type") != "commonjs":
            raise ValueError(f"{manifest_path}: package type must remain commonjs")
        return
    write_json(manifest_path, {"private": True, "type": "commonjs"})


def source_record(package: dict, version: str) -> str:
    """Render machine-readable provenance for one package family."""
    return json.dumps(
        {
            "author": package["author"],
            "commit": package["commit"],
            "license": package["license"],
            "marketplace_name": marketplace_name(package),
            "plugin_name": package["plugin_name"],
            "plugin_path": package["plugin_path"],
            "plugin_version": version,
            "repository": package["repository"],
            "snapshot_date": package["snapshot_date"],
            "stars": package["stars"],
            "targets": sorted(TARGETS),
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def marketplace_name(package: dict) -> str:
    """Return the unique local Claude marketplace name for one package."""
    return f"orax-{package['identifier'].replace('.', '-')}"


def package_readme(package: dict, version: str) -> str:
    """Render attribution and runtime requirements shipped inside the archive."""
    return f"""# {package["title"]}

{package["description"]}

This Ora Hook package installs the upstream Claude Code plugin
`{package["plugin_name"]}` from
[{package["repository"]}]({package["homepage"]}) at commit
`{package["commit"]}`. The upstream plugin version is `{version}`.

## Behaviour

On install, Ora runs the package-contained `hookctl` as `init`. It registers a
local Claude Code marketplace and installs `{package["plugin_name"]}` at user
scope. On uninstall, `hookctl` removes the plugin and the local marketplace
before Ora removes the package.

Claude Code must be available as `claude` (or `claude.exe`) on `PATH`. The
upstream Hook may also require Node.js, Python, or `npx`; see the upstream
README for the exact dependency and configuration of this Hook.

## Source

- Repository: `{package["repository"]}`
- Commit: `{package["commit"]}`
- Plugin path: `{package["plugin_path"]}`
- Stars snapshot: {package["stars"]} on {package["snapshot_date"]}
- License: {package["license"]}

The upstream license text is included as `UPSTREAM_*`; `SOURCE.json` records
the exact provenance used by the deterministic build.
"""


def package_manifest(package: dict, version: str, target: str, release: bool) -> str:
    """Render one installed-form or release-form marketplace manifest."""
    lines = [
        "resolver = 1",
        f"title = {toml_string(package['title'])}",
        f"identifier = {toml_string(package['identifier'])}",
        f"namespace = {toml_string(package['namespace'])}",
        'kind = "hook"',
        f"version = {toml_string(version)}",
        f"description = {toml_string(package['description'])}",
        f"homepage = {toml_string(package['homepage'])}",
        f"license = {toml_string(package['license'])}",
    ]
    if not release:
        lines += ["", "[artifact]", f"target = {toml_string(target)}"]
    return "\n".join(lines) + "\n"


def hook_config(executable: str) -> str:
    """Render the Hook configuration consumed by the Ora host."""
    return json.dumps(
        {
            "schemaVersion": 1,
            "hook": {
                "executable": f"assets/{executable}",
                "supportedAgents": ["claude-code"],
                "lifecycle": {
                    "init": {"args": ["install"]},
                    "deinit": {"args": ["uninstall"]},
                },
            },
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def create_template(package: dict, checkout: Path, template: Path) -> str:
    """Create the target-independent package tree and return plugin version."""
    source = checkout / package["plugin_path"]
    marketplace = template / "assets" / "claude-marketplace"
    plugin = marketplace / "plugin"
    plugin_manifest_path = source / ".claude-plugin" / "plugin.json"
    if not plugin_manifest_path.is_file():
        raise ValueError(f"{package['repository']}: plugin manifest is missing: {plugin_manifest_path}")
    upstream_manifest = load_json(plugin_manifest_path)
    if upstream_manifest.get("name") != package["plugin_name"]:
        raise ValueError(
            f"{package['repository']}: plugin name {upstream_manifest.get('name')!r} "
            f"does not match {package['plugin_name']!r}"
        )
    version = str(upstream_manifest.get("version", "1.0.0"))
    if not SEMVER.fullmatch(version):
        raise ValueError(f"{package['repository']}: invalid plugin version {version!r}")

    copy_selected(source, plugin, package.get("plugin_include"))
    ensure_module_type(plugin, package)
    patch_hook_commands(plugin, package)
    validate_tree(marketplace)
    write_json(
        marketplace / ".claude-plugin" / "marketplace.json",
        {
            "name": marketplace_name(package),
            "owner": {"name": "Ora Space"},
            "plugins": [
                {
                    "name": package["plugin_name"],
                    "source": "./plugin",
                    "description": package["description"],
                    "version": version,
                    "license": package["license"],
                }
            ],
        },
    )
    write_json(
        template / "assets" / "integration.json",
        {
            "marketplace": marketplace_name(package),
            "plugin": package["plugin_name"],
            "identifier": package["identifier"],
        },
    )
    (template / "README.md").write_text(package_readme(package, version), encoding="utf-8", newline="\n")
    (template / "SOURCE.json").write_text(source_record(package, version), encoding="utf-8", newline="\n")
    for relative in package["license_files"]:
        source_license = checkout / relative
        if not source_license.is_file():
            raise ValueError(f"{package['repository']}: missing license file {relative}")
        shutil.copyfile(source_license, template / ("UPSTREAM_" + relative.replace("/", "-")))
    validate_tree(template)
    return version


def build_hookctl(target: str, output: Path) -> Path:
    """Cross-compile the package-contained lifecycle helper for one target."""
    goos, goarch, name = TARGETS[target]
    binary = output / name
    run(
        go(),
        "build",
        "-trimpath",
        "-buildvcs=false",
        "-ldflags=-s -w",
        "-o",
        str(binary),
        ".",
        cwd=HOOKCTL,
        env={"GOOS": goos, "GOARCH": goarch, "CGO_ENABLED": "0"},
    )
    return binary


def archive_entries(stage: Path) -> list[tuple[Path, str]]:
    """Return sorted (source, archive name) pairs."""
    return [
        (path, path.relative_to(stage).as_posix())
        for path in sorted(stage.rglob("*"))
        if path.is_file()
    ]


def build_archive(package: dict, version: str, stage: Path, target: str, output: Path) -> tuple[Path, str]:
    """Write one deterministic ZIP-format .orax and return its path and digest."""
    archive_path = output / f"{package['identifier']}-{version}-{target}.orax"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source, arcname in sorted(archive_entries(stage), key=lambda entry: entry[1]):
            info = zipfile.ZipInfo(arcname, date_time=FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            executable = arcname.endswith("hookctl") or arcname.endswith(".sh")
            info.external_attr = (0o755 if executable else 0o644) << 16
            archive.writestr(info, source.read_bytes())
    return archive_path, hashlib.sha256(archive_path.read_bytes()).hexdigest()


def registry_entry(
    package: dict,
    version: str,
    digests: dict[str, str],
    registry_base: str,
) -> str:
    """Render a multi-target release-form marketplace listing."""
    lines = [package_manifest(package, version, "", release=True).rstrip(), ""]
    for target in sorted(digests):
        archive_name = f"{package['identifier']}-{version}-{target}.orax"
        lines += [
            "[[targets]]",
            f"target = {toml_string(target)}",
            f"url = {toml_string(registry_base.rstrip('/') + '/' + archive_name)}",
            f"sha256 = {toml_string(digests[target])}",
            "",
        ]
    return "\n".join(lines)


def write_registry(
    package: dict,
    version: str,
    digests: dict[str, str],
    registry_root: Path,
    registry_base: str,
) -> None:
    """Write one registry listing and its README."""
    directory = registry_root / package["identifier"]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "orax.toml").write_text(
        registry_entry(package, version, digests, registry_base), encoding="utf-8", newline="\n"
    )
    (directory / "README.md").write_text(package_readme(package, version), encoding="utf-8", newline="\n")


def load_catalog() -> list[dict]:
    """Load and validate all Hook package declarations."""
    catalog = tomllib.loads(CATALOG.read_text(encoding="utf-8"))
    packages = catalog.get("packages")
    if not isinstance(packages, list) or len(packages) != 10:
        raise ValueError("catalog.toml must contain exactly ten [[packages]] entries")
    seen: set[str] = set()
    result: list[dict] = []
    for package in packages:
        completed = dict(package)
        completed["namespace"] = catalog["namespace"]
        completed["snapshot_date"] = catalog["snapshot_date"]
        completed["identifier"] = f"top-hooks.{completed['slug']}"
        if completed["identifier"] in seen:
            raise ValueError(f"duplicate identifier: {completed['identifier']}")
        seen.add(completed["identifier"])
        if not re.fullmatch(r"[0-9a-f]{40}", completed["commit"]):
            raise ValueError(f"{completed['repository']}: commit must be a full lowercase SHA")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", completed["plugin_name"]):
            raise ValueError(f"{completed['repository']}: invalid plugin name")
        if not isinstance(completed["license_files"], list) or not completed["license_files"]:
            raise ValueError(f"{completed['repository']}: license_files must not be empty")
        result.append(completed)
    return result


def build_all(packages: list[dict], output: Path) -> list[tuple[dict, str, dict[str, str]]]:
    """Build every package for every target in an isolated workspace."""
    output.mkdir(parents=True, exist_ok=True)
    results: list[tuple[dict, str, dict[str, str]]] = []
    with tempfile.TemporaryDirectory(prefix="ora-top-hooks-", ignore_cleanup_errors=True) as temporary:
        temp = Path(temporary)
        binaries: dict[str, Path] = {}
        checkouts: dict[tuple[str, str], Path] = {}
        for target in TARGETS:
            binary_dir = temp / "bin" / target
            binary_dir.mkdir(parents=True, exist_ok=True)
            binaries[target] = build_hookctl(target, binary_dir)

        for package in packages:
            key = (package["repository"], package["commit"])
            checkout = checkouts.get(key)
            if checkout is None:
                checkout = temp / "repos" / package["repository"].replace("/", "__") / package["commit"]
                fetch_repository(package["repository"], package["commit"], checkout)
                checkouts[key] = checkout

            template = temp / "templates" / package["slug"]
            version = create_template(package, checkout, template)
            digests: dict[str, str] = {}
            for target, (_goos, _goarch, name) in TARGETS.items():
                stage = temp / "stages" / f"{package['slug']}-{target}"
                shutil.copytree(template, stage)
                shutil.copyfile(binaries[target], stage / "assets" / name)
                (stage / "assets" / "config.json").write_text(hook_config(name), encoding="utf-8", newline="\n")
                (stage / "orax.toml").write_text(
                    package_manifest(package, version, target, release=False),
                    encoding="utf-8",
                    newline="\n",
                )
                archive_path, digest = build_archive(package, version, stage, target, output)
                digests[target] = digest
                print(f"{archive_path.name}  sha256={digest}")
            results.append((package, version, digests))
    return results


def check_all(
    packages: list[dict],
    results: list[tuple[dict, str, dict[str, str]]],
    registry_root: Path,
) -> None:
    """Verify committed archives and every multi-target registry digest."""
    if len(results) != len(packages):
        raise ValueError("build did not produce every package")
    for package, version, digests in results:
        for target, digest in digests.items():
            archive = ROOT / "dist" / f"{package['identifier']}-{version}-{target}.orax"
            if not archive.is_file():
                raise ValueError(f"committed archive is missing: {archive}")
            actual = hashlib.sha256(archive.read_bytes()).hexdigest()
            if actual != digest:
                raise ValueError(f"archive is stale: {archive} ({actual} != {digest})")
        listing = registry_root / package["identifier"] / "orax.toml"
        if not listing.is_file():
            raise ValueError(f"registry listing is missing: {listing}")
        release = tomllib.loads(listing.read_text(encoding="utf-8"))
        by_target = {entry["target"]: entry for entry in release.get("targets", [])}
        if set(by_target) != set(TARGETS):
            raise ValueError(f"registry target set is stale: {listing}")
        for target, digest in digests.items():
            entry = by_target[target]
            if entry.get("sha256") != digest:
                raise ValueError(f"registry digest is stale: {listing} ({target})")
            expected_name = f"{package['identifier']}-{version}-{target}.orax"
            if not str(entry.get("url", "")).endswith("/" + expected_name):
                raise ValueError(f"registry URL does not name the archive: {listing} ({target})")
            if not str(entry["url"]).startswith("https://"):
                raise ValueError(f"registry URL is not HTTPS: {listing} ({target})")
    print(f"verified {len(results)} packages across {len(TARGETS)} targets")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    parser.add_argument("--registry-root", type=Path, default=ROOT.parents[1] / "registry" / "t")
    parser.add_argument("--write-registry", action="store_true")
    parser.add_argument("--registry-base")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.write_registry and not args.registry_base:
        parser.error("--write-registry requires --registry-base")
    if args.registry_base and not args.registry_base.startswith("https://"):
        parser.error("--registry-base must be HTTPS")

    packages = load_catalog()
    if args.check:
        with tempfile.TemporaryDirectory(
            prefix="ora-top-hooks-check-", ignore_cleanup_errors=True
        ) as temporary:
            results = build_all(packages, Path(temporary))
            check_all(packages, results, args.registry_root)
        return 0

    results = build_all(packages, args.out)
    if args.write_registry:
        for package, version, digests in results:
            write_registry(package, version, digests, args.registry_root, args.registry_base)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, tomllib.TOMLDecodeError, zipfile.BadZipFile) as error:
        print(f"top-hooks build failed: {error}", file=sys.stderr)
        raise SystemExit(1)
