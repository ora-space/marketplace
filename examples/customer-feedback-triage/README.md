# Customer Feedback Triage

`official/ora-space.customer-feedback-triage` is a `kind = "workflow"` plugin for
customer-success and support teams. It turns raw customer feedback into a
reviewable triage, handling plan, and customer reply.

## Workflow

| Node | Purpose |
| --- | --- |
| 开始：客户反馈 | Accepts required feedback plus optional customer and context fields. |
| 分诊与风险评估 | Assigns P0-P3 priority, classifies the issue, assesses impact, lists missing information, and proposes a handling path. |
| 处置建议与客户回复 | Produces internal next actions and a customer-ready reply without inventing facts or promises. |
| 输出处理材料 | Exposes the complete Markdown result as `result`. |

The workflow does not read or modify project files. Select any Project when
starting it; the project is the run's workspace boundary, not an input source.
The Agent nodes target the installed `official/ora-space.opencode` executor and
use that executor's default model; the package ships no model ID, credential,
MCP, Skill, or deployment-specific configuration.

## Requirements

- The `official/ora-space.opencode` Agent installed in the space, with a
  configured model.
- Feedback text suitable for the configured model provider. Do not paste
  credentials, access tokens, or unnecessary personal data.

The workflow is instructed not to invent logs, ticket IDs, metrics, root
causes, resolution times, refunds, or completed actions. The generated customer
reply must be reviewed before it is sent.

## Install and remove

Installing the package imports
`assets/workflows/customer-feedback-triage.json` as an editable workflow with a
published snapshot. Removing the plugin only removes the plugin selection; the
imported workflow and its run history remain user data.

## Validate and build

```sh
python3 ../workflow-examples/tools/validate.py .
python3 ../workflow-examples/tools/build.py --package . --out dist
```

## License

Apache-2.0. See [the repository license](../../../LICENSE).

