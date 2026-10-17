# ora-space.workflow-examples

Official example workflows for Ora, delivered as a `kind = "workflow"` plugin
package. The package starts no process: installing it imports each document in
`assets/workflows/` into the workflow library as an editable workflow with a
published snapshot. The imported workflows are user data and survive
uninstalling the package.

## Documents

| Document | Shape | What it needs |
| --- | --- | --- |
| `hello-agent.json` | Start → Agent → Output | A personal default executor. The agent uses the implicit `default` slot. |
| `named-slot.json` | Start → Agent → Output | A personal `writer` slot mapping. The agent declares and references the slot. |

Both documents take one run input, pass it to the agent through a prompt
template variable, and expose the agent result from the Output node. Neither
carries credentials, deployment-specific configuration, or MCP/skill
dependencies.

The examples are intentionally linear. A branching example will be added once
the shared condition-selector shape is settled; publishing an example against
an interim shape would teach the wrong schema.

## Installing

- **Cloud.** A space administrator explicitly installs the package from its
  plugin source. Cloud downloads the `.orax` itself, verifies its SHA-256 and
  imports every document into the tenant. No live workspace is required, and
  nothing is installed automatically for new spaces. Documents already imported
  from the same source are skipped on a repeat install or upgrade.
- **Desktop.** Importing the `.orax` locally installs the plugin and imports
  the documents into the local workflow library. The package is universal: it
  ships no platform-specific artifact.

## Requirements and failure feedback

The first document needs only the runner's personal default executor. The
second declares the `writer` slot with a description and a display-only hint;
a runner without a mapping for it is refused at start with the slot name, the
description the author wrote, and the nodes that depend on it. Map the slot to
one of the runner's own connections and models, then start the same snapshot
again — nothing about the document changes.

Cloud currently sends an agent prompt verbatim and does not interpolate
`{{#...#}}` template variables. These documents are written against the final
prompt contract, so end-to-end execution waits for variable passing to land in
the cloud session runtime. They also use the cloud executor-slot schema;
Desktop can import and edit them, but the intended runtime is Cloud.

## Layout

```text
orax.toml
assets/workflows/hello-agent.json
assets/workflows/named-slot.json
tools/validate.py
tools/build.py
tools/test_validate.py
```

Only direct `*.json` children of `assets/workflows/` are documents; other files
and subdirectories in that directory are ignored. The package may carry 1 to
256 documents.

## Validate and build

```sh
python3 tools/validate.py
python3 -m unittest discover -s tools -p 'test_*.py'
python3 tools/build.py --out dist
```

`validate.py` mirrors the first-phase publish gate Cloud applies to an imported
document, so a package that passes is one Cloud accepts. `build.py` writes a
reproducible `.orax` (sorted entries, fixed timestamps) and prints its SHA-256.
Pass `--base-url https://…` to also write `dist/manifest.toml`, the release
form with the download URL and digest a registry entry needs.

## License

Apache-2.0. See [the repository license](../../../LICENSE).
