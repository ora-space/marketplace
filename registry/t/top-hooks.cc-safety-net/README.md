# CC Safety Net

Block destructive commands, secret access, and unsafe agent actions before tool calls run. From kenryu42/cc-safety-net.

This Ora Hook package installs the upstream Claude Code plugin
`cc-safety-net` from
[kenryu42/cc-safety-net](https://github.com/kenryu42/cc-safety-net) at commit
`0fb31bdf3f5b6f308b51bb0a9807f572fb4f510e`. The upstream plugin version is `2.7.3`.

## Behaviour

On install, Ora runs the package-contained `hookctl` as `init`. It registers a
local Claude Code marketplace and installs `cc-safety-net` at user
scope. On uninstall, `hookctl` removes the plugin and the local marketplace
before Ora removes the package.

Claude Code must be available as `claude` (or `claude.exe`) on `PATH`. The
upstream Hook may also require Node.js, Python, or `npx`; see the upstream
README for the exact dependency and configuration of this Hook.

## Source

- Repository: `kenryu42/cc-safety-net`
- Commit: `0fb31bdf3f5b6f308b51bb0a9807f572fb4f510e`
- Plugin path: `.`
- Stars snapshot: 1910 on 2026-11-04
- License: MIT

The upstream license text is included as `UPSTREAM_*`; `SOURCE.json` records
the exact provenance used by the deterministic build.
