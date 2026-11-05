"""Reject changes to a published registry release even when its listing moves."""

import subprocess
import sys
import tomllib


def digests(ref):
    paths = subprocess.check_output(
        ["git", "ls-tree", "-rz", "--name-only", ref, "--", "registry"]
    ).decode().split("\0")
    result = {}
    for path in paths:
        if not path.endswith("/orax.toml"):
            continue
        listing = tomllib.loads(subprocess.check_output(
            ["git", "show", f"{ref}:{path}"]
        ).decode())
        for item in listing.get("targets", [listing]):
            key = (listing["identifier"], listing["version"], item.get("target", ""))
            if key in result:
                raise ValueError(f"duplicate release target {key} in {ref}")
            result[key] = item["sha256"]
    return result


if __name__ == "__main__":
    published, candidate = map(digests, sys.argv[1:])
    changed = sorted(k for k in published.keys() & candidate.keys()
                     if published[k] != candidate[k])
    if changed:
        sys.exit(f"Published SHA-256 changed; bump the package version: {changed}")
