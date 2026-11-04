# Requirement Decomposition

`official/ora-space.requirement-decomposition` is a `kind = "workflow"` plugin
that turns one large requirement into assignable subtasks.

## Workflow

| Node | Purpose |
| --- | --- |
| 开始：大需求 | Accepts the requirement as a required paragraph. |
| 拆分需求与验收条件 | Reads the repository README and emits 3-5 subtasks with scope and acceptance criteria. |
| 输出子任务 | Exposes the Agent's JSON answer as `tasks`. |

The final `tasks` value is the Agent's JSON text:

```json
{"tasks":[{"title":"…","description":"…"}]}
```

Ora's task decomposition consumer accepts this shape, including when the
`tasks` value arrives as a JSON string. The workflow intentionally uses plain
text output instead of a structured-output contract so the same package is
accepted by both the current Cloud publish gate and v2.

## Requirements

- A Project selected when the workflow starts. The Agent reads its README but
  does not modify files.
- A configured default Agent executor and model for the runner.

The workflow is read-only. It does not access the network or install
dependencies.

## Install and remove

Installing the package imports `assets/workflows/requirement-decomposition.json`
as an editable workflow with a published snapshot. Removing the plugin only
removes the plugin selection; the imported workflow and its run history remain
user data.

## Validate and build

```sh
python3 ../workflow-examples/tools/validate.py .
python3 ../workflow-examples/tools/build.py --package . --out dist
```

## License

Apache-2.0. See [the repository license](../../../LICENSE).

