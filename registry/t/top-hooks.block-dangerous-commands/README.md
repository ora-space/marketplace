# Block Dangerous Commands

Stop catastrophic shell commands such as recursive home deletion, disk wipes, fork bombs, and force pushes to main. From karanb192/claude-code-hooks.

This Ora Hook package installs the upstream Claude Code plugin
`block-dangerous-commands` from
[karanb192/claude-code-hooks](https://github.com/karanb192/claude-code-hooks) at commit
`57a28c7687305e4a9b9dd50490e9b3c552c71ca4`. The upstream plugin version is `1.0.0`.

## Behaviour

On install, Ora runs the package-contained `hookctl` as `init`. It registers a
local Claude Code marketplace and installs `block-dangerous-commands` at user
scope. On uninstall, `hookctl` removes the plugin and the local marketplace
before Ora removes the package.

Claude Code must be available as `claude` (or `claude.exe`) on `PATH`. The
upstream Hook may also require Node.js, Python, or `npx`; see the upstream
README for the exact dependency and configuration of this Hook.

## Source

- Repository: `karanb192/claude-code-hooks`
- Commit: `57a28c7687305e4a9b9dd50490e9b3c552c71ca4`
- Plugin path: `plugins/block-dangerous-commands`
- Stars snapshot: 572 on 2026-11-04
- License: MIT

The upstream license text is included as `UPSTREAM_*`; `SOURCE.json` records
the exact provenance used by the deterministic build.
