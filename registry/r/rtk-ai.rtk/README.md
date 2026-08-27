# RTK

[RTK](https://github.com/rtk-ai/rtk) as an Ora Hook Plugin. RTK rewrites shell commands to
invoke a bare `rtk` command and filters command output before it reaches an LLM context window.

This listing targets `x86_64-pc-windows-msvc` and embeds RTK `0.45.0`. The Hook Plugin version
is `0.1.0`, independent from the embedded tool version.

## Local tracking behavior

RTK `0.45.0` stores local command-tracking data in a SQLite database and does not honor its
declared tracking-disable setting. The Hook is inert in the installation-only milestone, but a
future Agent Plugin consumer must redirect RTK's database to Ora-managed data, disable tee and
telemetry, and disclose the local retention of original commands and project paths.
