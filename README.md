# codex-cli-helper

Small local wrapper around the Codex app-server protocol. It creates a durable,
phone-visible Codex task, starts the initial turn, prints the identifiers, and
exits while the app-server continues the task.

The CLI uses [Cyclopts](https://cyclopts.readthedocs.io/) because its typed
function signatures and docstrings produce built-in help, shell completion, and
generated reference documentation with little boilerplate.

## Install

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Start a task

```bash
codex-cli-helper start-task \
  --cwd /root/Projects/ToolRelay/.worktrees/platform-issue-2 \
  --model gpt-5.6-sol \
  --sandbox danger-full-access \
  --approval-policy never \
  --prompt 'Work only on the assigned issue. Read AGENTS.md, implement it, verify it, and leave the branch ready for review.'
```

Use `--json` for scripting:

```bash
codex-cli-helper start-task --cwd /path/to/worktree --prompt '...' --json
```

The default socket is `/root/.codex/app-server-control/app-server-control.sock`.
Override it with `--socket` when the daemon uses another Unix socket. The
initialization handshake uses the local daemon's existing Codex login; no API
key is stored or passed by this tool.

The command does not create a Git worktree itself. Create or select the isolated
worktree first, then pass it as `--cwd`. This keeps repository policy and branch
ownership explicit.

## Generated documentation

```bash
PYTHONPATH=src cyclopts generate-docs src/codex_cli_helper/cli.py \
  --output docs/cli.md --usage-name codex-cli-helper
```

## Protocol scope

This targets the Codex app-server protocol shipped with the local CLI. The
protocol is version-sensitive, so errors are surfaced instead of silently
falling back to a different model or transport. It intentionally implements
only `initialize`, `thread/start`, and `turn/start`.
