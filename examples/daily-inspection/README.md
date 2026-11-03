# ora-space.daily-inspection

Official read-only workflow for a daily operations inspection. The workflow
checks the selected project's service files and logs, then writes a Markdown
report with the observed status, risks, and suggested follow-up.

The package is a `kind = "workflow"` plugin. Installing it imports
`assets/workflows/daily-inspection.json` into the workflow library as an
editable workflow with a published snapshot. It does not start a process and
ships no credentials, model IDs, or deployment-specific configuration.

## Workflow

| Node | Purpose |
| --- | --- |
| 开始：每日巡检 | Accepts the inspection request as the run input. |
| 检查服务与资源 | Reads the project's service evidence and runs the read-only inspection command available in the project. |
| 汇总风险与巡检报告 | Produces the complete Markdown report in the final assistant response. |
| 输出 | Exposes the report as the workflow result. |

The agent uses the implicit `default` executor slot. The workflow never edits
files, changes configuration, or attempts a repair.

## Requirements

- A Project selected at run or schedule time.
- A configured default Agent executor and model for the runner.
- A project that contains the service files and read-only inspection entry
  point the workflow is meant to inspect. The agent reports what it can verify
  and does not invent missing measurements.

The workflow is suitable for a scheduled task: select a published version and
a Project, set the cadence, and each occurrence creates an independent run.

## Validate and build

The marketplace's shared workflow validator and deterministic builder live in
the existing `examples/workflow-examples/tools` directory. From this package:

```sh
python3 ../workflow-examples/tools/validate.py .
python3 ../workflow-examples/tools/build.py --package . --out dist
```

Only direct `*.json` children of `assets/workflows/` become workflow documents.

## License

Apache-2.0. See [the repository license](../../../LICENSE).
