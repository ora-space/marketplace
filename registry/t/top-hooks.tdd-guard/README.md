# TDD Guard

Automated test-driven development enforcement for Claude Code. From nizos/tdd-guard.

This Ora Hook package installs the upstream Claude Code plugin
`tdd-guard` from
[nizos/tdd-guard](https://github.com/nizos/tdd-guard) at commit
`ffb7026c8f7e335e2914461fce9ec3f897a87125`. The upstream plugin version is `1.3.0`.

## Behaviour

On install, Ora runs the package-contained `hookctl` as `init`. It registers a
local Claude Code marketplace and installs `tdd-guard` at user
scope. On uninstall, `hookctl` removes the plugin and the local marketplace
before Ora removes the package.

Claude Code must be available as `claude` (or `claude.exe`) on `PATH`. The
upstream Hook may also require Node.js, Python, or `npx`; see the upstream
README for the exact dependency and configuration of this Hook.

## Source

- Repository: `nizos/tdd-guard`
- Commit: `ffb7026c8f7e335e2914461fce9ec3f897a87125`
- Plugin path: `plugin`
- Stars snapshot: 2373 on 2026-11-04
- License: MIT

The upstream license text is included as `UPSTREAM_*`; `SOURCE.json` records
the exact provenance used by the deterministic build.
