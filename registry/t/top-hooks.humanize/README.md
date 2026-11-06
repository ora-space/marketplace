# Humanize

Block AI buzzwords and machine-sounding prose before file writes, commits, and generated messages land. From fcakyon/claude-codex-settings.

This Ora Hook package installs the upstream Claude Code plugin
`humanize` from
[fcakyon/claude-codex-settings](https://github.com/fcakyon/claude-codex-settings) at commit
`4f2b4bc9a74024397b4688cbafd1ae538a83a5fb`. The upstream plugin version is `1.2.8`.

## Behaviour

On install, Ora runs the package-contained `hookctl` as `init`. It registers a
local Claude Code marketplace and installs `humanize` at user
scope. On uninstall, `hookctl` removes the plugin and the local marketplace
before Ora removes the package.

Claude Code must be available as `claude` (or `claude.exe`) on `PATH`. The
upstream Hook may also require Node.js, Python, or `npx`; see the upstream
README for the exact dependency and configuration of this Hook.

## Source

- Repository: `fcakyon/claude-codex-settings`
- Commit: `4f2b4bc9a74024397b4688cbafd1ae538a83a5fb`
- Plugin path: `plugins/humanize`
- Stars snapshot: 1198 on 2026-11-04
- License: Apache-2.0

The upstream license text is included as `UPSTREAM_*`; `SOURCE.json` records
the exact provenance used by the deterministic build.
