# Prompt Improver

Clarify vague prompts and inject targeted context before Claude starts work. From severity1/claude-code-prompt-improver.

This Ora Hook package installs the upstream Claude Code plugin
`prompt-improver` from
[severity1/claude-code-prompt-improver](https://github.com/severity1/claude-code-prompt-improver) at commit
`50aae187bb4f08b852f318234b654df3332726a4`. The upstream plugin version is `0.6.3`.

## Behaviour

On install, Ora runs the package-contained `hookctl` as `init`. It registers a
local Claude Code marketplace and installs `prompt-improver` at user
scope. On uninstall, `hookctl` removes the plugin and the local marketplace
before Ora removes the package.

Claude Code must be available as `claude` (or `claude.exe`) on `PATH`. The
upstream Hook may also require Node.js, Python, or `npx`; see the upstream
README for the exact dependency and configuration of this Hook.

## Source

- Repository: `severity1/claude-code-prompt-improver`
- Commit: `50aae187bb4f08b852f318234b654df3332726a4`
- Plugin path: `.`
- Stars snapshot: 1966 on 2026-11-04
- License: MIT

The upstream license text is included as `UPSTREAM_*`; `SOURCE.json` records
the exact provenance used by the deterministic build.
