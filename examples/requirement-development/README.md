# Requirement Development

`official/ora-space.requirement-development` is a `kind = "workflow"` plugin for
delivering a software requirement inside the project selected at run time.

## Workflow

| Node | Purpose |
| --- | --- |
| 开始：需求 | Accepts the requirement as a required paragraph. |
| 理解需求与制定计划 | Reads the repository and produces an implementation plan and acceptance checklist. |
| 实现需求 | Changes the repository and updates automated tests. |
| 运行测试与交付说明 | Runs the repository's tests, fixes failures within scope, and returns a delivery report. |
| 输出交付报告 | Exposes the final delivery report as `delivery`. |

All Agent nodes share the run's workspace, so implementation and verification
see the same files. The Agent nodes target the installed
`official/ora-space.opencode` executor and use that executor's default model;
the package pins no model ID, credential, MCP, Skill, or deployment-specific
configuration.

## Requirements

- A Project selected when the workflow starts. The Project should contain the
  source tree and test command the requirement refers to.
- The `official/ora-space.opencode` Agent installed in the space, with a
  configured model.

The workflow is instructed not to install dependencies, access the network, or
commit/push changes. Review the produced diff before accepting the result.

## Install and remove

Installing the package imports `assets/workflows/requirement-development.json`
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

