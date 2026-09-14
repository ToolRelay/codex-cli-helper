# codex-cli-helper

A small, local Python command-line toolkit for working with the Codex
app-server. It is intentionally a thin protocol adapter: commands expose
Codex capabilities in a scriptable form while callers retain ownership of
workflow policy, scheduling, and project decisions.

The initial release provides a small task lifecycle surface: `start-task`
creates a durable thread and starts its first turn, `list-tasks` reads task
summaries, and `delete-task` permanently removes a task. The package is
structured so additional app-server capabilities can be added without
coupling the helper to a particular project management system.

The CLI uses [Cyclopts](https://cyclopts.readthedocs.io/) because typed
signatures and docstrings provide built-in help, shell completion, and
generated reference documentation with little boilerplate.

## Install

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Task lifecycle commands

### Start a task

```bash
codex-cli-helper start-task \
  --cwd /path/to/project \
  --model gpt-5.6-sol \
  --sandbox danger-full-access \
  --approval-policy never \
  --prompt 'Work on the requested task and leave the result ready for review.'
```

Use `--json` for scripting:

```bash
codex-cli-helper start-task --cwd /path/to/project --prompt '...' --json
```

### List tasks

```bash
codex-cli-helper list-tasks --cwd /path/to/project
codex-cli-helper list-tasks --include-non-interactive --json
```

By default, `list-tasks` returns active (non-archived) tasks. Use
`--archived archived` to list archived tasks, `--source-kind` to select one or
more protocol source kinds, and `--cursor` to continue a paginated response.

### Delete a task

```bash
codex-cli-helper delete-task --thread-id THREAD_ID --yes
```

Deletion is permanent, so `--yes` is required. Add `--json` when the result is
being consumed by another program.

The default socket is
`/root/.codex/app-server-control/app-server-control.sock`. Override it with
`--socket` when the daemon uses another Unix socket. The initialization
handshake uses the local daemon's existing Codex login; no API key is stored or
passed by this tool.

`--cwd` is simply the directory in which Codex should operate. The helper does
not impose project layout, branching, or workflow policy.

## Generated documentation

```bash
PYTHONPATH=src cyclopts generate-docs src/codex_cli_helper/cli.py \
  --output docs/cli.md --usage-name codex-cli-helper
```

## Design scope

This targets the Codex app-server protocol shipped with the local CLI. The
protocol is version-sensitive, so errors are surfaced instead of silently
falling back to a different model or transport. The current implementation
uses `initialize`, `thread/start`, `turn/start`, `thread/list`, and
`thread/delete`; future commands can build on the same client without changing
the authentication or transport boundary.
