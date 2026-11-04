# GitHub Top 10 Agent Hooks

This directory builds ten real Ora Hook plugins from high-starred Claude Code
Hook projects on 2026-11-04. Every package installs an upstream Claude Code
plugin from a pinned commit; no hook is represented by a static placeholder.

Each package contains a cross-platform `hookctl` executable, the pinned
upstream plugin, the upstream license, and a `SOURCE.json`. `init` registers a
package-local Claude Code marketplace and installs one plugin at user scope.
`deinit` removes that plugin and marketplace before the Ora package is deleted.

| Rank | Hook | Upstream repository | Stars | License |
| ---: | --- | --- | ---: | --- |
| 1 | TDD Guard | [nizos/tdd-guard](https://github.com/nizos/tdd-guard) | 2,373 | MIT |
| 2 | Prompt Improver | [severity1/claude-code-prompt-improver](https://github.com/severity1/claude-code-prompt-improver) | 1,966 | MIT |
| 3 | CC Safety Net | [kenryu42/cc-safety-net](https://github.com/kenryu42/cc-safety-net) | 1,910 | MIT |
| 4 | Humanize | [fcakyon/claude-codex-settings](https://github.com/fcakyon/claude-codex-settings) | 1,198 | Apache-2.0 |
| 5 | Block Dangerous Commands | [karanb192/claude-code-hooks](https://github.com/karanb192/claude-code-hooks) | 572 | MIT |
| 6 | Protect Secrets | [karanb192/claude-code-hooks](https://github.com/karanb192/claude-code-hooks) | 572 | MIT |
| 7 | Git Safety | [karanb192/claude-code-hooks](https://github.com/karanb192/claude-code-hooks) | 572 | MIT |
| 8 | Protect Tests | [karanb192/claude-code-hooks](https://github.com/karanb192/claude-code-hooks) | 572 | MIT |
| 9 | Config Guard | [karanb192/claude-code-hooks](https://github.com/karanb192/claude-code-hooks) | 572 | MIT |
| 10 | Auto Stage | [karanb192/claude-code-hooks](https://github.com/karanb192/claude-code-hooks) | 572 | MIT |

Several packages share `karanb192/claude-code-hooks` because it publishes
independently installable, self-contained Hooks. Duplicating a source is
preferable to packaging a repository that only installs through a bespoke
project setup or depends on a missing native binary.

Higher-starred projects excluded from this batch:

- `Dicklesworthstone/destructive_command_guard`: its license adds an
  OpenAI/Anthropic-only restriction, so it is not redistributable under the
  marketplace's OSI-license criterion.
- `disler/claude-code-hooks-mastery` and several other high-starred showcase
  repositories: no repository license.
- `parcadei/Continuous-Claude-v3`: no Claude Code plugin marketplace or
  standalone installer; its hooks depend on the repository's broader runtime.
- `CloudAI-X/claude-workflow-v2`: its Bash hooks assume a POSIX shell and its
  Python hooks invoke `python3` directly, which is not portable on Windows.
- `vshulcz/deja-vu`: the plugin shell bridges to a separate `deja` binary that
  the plugin does not ship.
- `SethGammon/Citadel` and `sangrokjung/claude-forge`: the Claude plugin
  manifests do not install their generated Hook sets directly.
- `aannoo/hcom`: the marketplace plugin contains the skill surface only; the
  Hook module requires an hcom-managed interactive process.
- `carlrannaberg/claudekit`: installation requires a global npm CLI and a
  project setup step; the repository does not publish a Claude plugin.

## Requirements

- Claude Code 2.1 or newer, with `claude` (or `claude.exe`) on `PATH`.
- Node.js for JavaScript Hooks; Python 3 for `humanize`; `npx` for TDD Guard.
- The user must authorize Ora to run the package executable. Hook packages
  execute outside Ora's plugin sandbox and may edit Claude Code configuration.

## Build

```sh
python3 tools/build.py
```

With `--write-registry`, the builder also writes
`registry/t/top-hooks.<slug>/orax.toml` and README files. The URL base must
point at the commit that contains the archives:

```sh
python3 tools/build.py \
  --write-registry \
  --registry-base https://raw.githubusercontent.com/ora-space/marketplace/<commit>/examples/top-hooks/dist
```

`--check` rebuilds every archive in a temporary directory and verifies both the
committed archive digest and every target digest in each registry listing.

Registry artifacts are pinned to the commit that added them. Merge this change
with a merge commit so that commit remains reachable from `main`; squash and
rebase merges would break the pinned raw URLs.

## Licensing

Each archive retains the selected upstream plugin, the upstream license text,
and a `SOURCE.json` with the exact repository, commit, stars snapshot, plugin
path, version, and marketplace name. The upstream license governs the bundled
plugin code.
