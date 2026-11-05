# ora-space.daily-inspection

Read-only daily inspection workflow for a Project. The workflow inspects the
project's service evidence, produces a Markdown report, and never edits files
or attempts a repair.

Installing the package imports the workflow into the workflow library. Running
or scheduling it requires a Project and the installed
`official/ora-space.opencode` Agent plugin; the agent nodes do not pin a model.
