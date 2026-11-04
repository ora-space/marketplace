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
| 2 | [mattpocock/skills](https://github.com/mattpocock/skills) | 311,835 | MIT | `tdd` |
| 3 | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | 183,961 | MIT | `ponytail` |
| 4 | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 144,899 | MIT | `ui-ux-pro-max` |
| 5 | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | 117,314 | Apache-2.0 | `caveman` |
| 6 | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | 113,117 | MIT | `code-review-and-quality` |
| 7 | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | 101,823 | Apache-2.0 | `impeccable` |
| 8 | [tt-a1i/archify](https://github.com/tt-a1i/archify) | 93,234 | Apache-2.0 | `archify` |
| 9 | [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design) | 64,786 | MIT | `diagram-design` |
| 10 | [blader/humanizer](https://github.com/blader/humanizer) | 64,540 | MIT | `humanizer` |

Repositories that merely carry a `SKILL.md` as an ancillary file, or whose
license does not allow redistribution, are excluded. Stars are a snapshot,
not a live feed.

## Build

```sh
python3 tools/build.py
```

With `--write-registry`, the builder also writes the corresponding
`registry/t/top-skills/<slug>/orax.toml` and README files. The URL base must
point at the commit that contains the archives:

```sh
python3 tools/build.py \
  --write-registry \
  --registry-base https://raw.githubusercontent.com/ora-space/marketplace/<commit>/examples/top-skills/dist
```

`--check` rebuilds every archive and verifies both the committed archive digest
and the digest in each registry listing.

## Licensing

Each archive retains the selected skill's upstream files, the upstream license
text, and a `SOURCE.json` with the exact repository, commit, stars snapshot and
skill path. See the upstream license for the terms that govern each skill.
