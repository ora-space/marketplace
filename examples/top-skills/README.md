# GitHub Top 10 Agent Skills

This directory builds ten static Ora Skill plugins from the ten highest-starred
repositories on 2026-11-04 whose primary distribution is Agent Skills, whose
license permits redistribution, and whose selected skill contains a real
`SKILL.md`.

Each package contributes exactly one skill under `assets/<name>/SKILL.md`. The
archives are deterministic: entries are sorted, timestamps are fixed,
permissions are normalized, and the build pins every upstream repository to a
commit in [`catalog.toml`](catalog.toml).

| Rank | Upstream repository | Stars | License | Skill |
| ---: | --- | ---: | --- | --- |
| 1 | [obra/superpowers](https://github.com/obra/superpowers) | 312,020 | MIT | `brainstorming` |
| 2 | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | 183,961 | MIT | `ponytail` |
| 3 | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 144,899 | MIT | `ui-ux-pro-max` |
| 4 | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | 117,314 | Apache-2.0 | `caveman` |
| 5 | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | 113,117 | MIT | `code-review-and-quality` |
| 6 | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | 101,823 | Apache-2.0 | `impeccable` |
| 7 | [tt-a1i/archify](https://github.com/tt-a1i/archify) | 93,234 | Apache-2.0 | `archify` |
| 8 | [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design) | 64,786 | MIT | `diagram-design` |
| 9 | [blader/humanizer](https://github.com/blader/humanizer) | 64,540 | MIT | `humanizer` |
| 10 | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | 58,383 | MIT | `copywriting` |

Repositories that merely carry a `SKILL.md` as an ancillary file, or whose
license does not allow redistribution, are excluded. Stars are a snapshot,
not a live feed.

Notable exclusions from the same snapshot:

- `morluto/rea` (428,224 stars): the repository primarily ships the REA
  application and MCP server; its `.agents/skills` directory is internal
  product guidance rather than a portable skill package.
- `anthropics/skills` (187,199 stars): GitHub reports no repository license,
  so its contents cannot be redistributed here.
- `mattpocock/skills` (311,835 stars): the repository is already present in the
  official marketplace as `official/mattpocock.skills`; adding another package
  would duplicate it. The next ranked skill is used instead.
- `career-ops-hq/career-ops` (79,967 stars): its skill expects the repository's
  root `AGENTS.md`, `modes/` and runtime files, so extracting only the selected
  skill directory would produce an installable but non-working package.
  `blader/humanizer` is the next self-contained, licensed skill repository.

## Build

```sh
python3 tools/build.py
```

With `--write-registry`, the builder also writes the corresponding
`registry/t/top-skills.<slug>/orax.toml` and README files. The URL base must
point at the commit that contains the archives:

```sh
python3 tools/build.py \
  --write-registry \
  --registry-base https://raw.githubusercontent.com/ora-space/marketplace/<commit>/examples/top-skills/dist
```

`--check` rebuilds every archive and verifies both the committed archive digest
and the digest in each registry listing.

Registry artifacts are pinned to the commit that added them. Merge this change
with a merge commit so that commit remains reachable from `main`; squash and
rebase merges would break the pinned raw URLs.

The builder refuses to publish when a contributed Skill name collides with a
Skill already published by another registry package. It verifies the existing
archive SHA-256 before reading its `assets/<skill>/SKILL.md` names.

Packaging also removes upstream-only material that is not used by the selected
skill: archify's pre-rendered example HTML and localized example pages,
copywriting's evals, humanizer's repository metadata and maintenance scripts,
and UI/UX Pro Max's test suite and data validator. The excluded path patterns
are recorded in each package's `SOURCE.json`.

## Licensing

Each archive retains the selected skill's upstream files, the upstream license
text, and a `SOURCE.json` with the exact repository, commit, stars snapshot and
skill path. See the upstream license for the terms that govern each skill.
