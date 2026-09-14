# codex-cli-helper

A small, local Python command-line toolkit for working with the Codex
app-server. It is intentionally a thin protocol adapter: commands expose
Codex capabilities in a scriptable form while callers retain ownership of
workflow policy, scheduling, and project decisions.

The initial release provides `start-task`, which creates a durable thread,
starts its first turn, prints the identifiers, and exits while the app-server
continues the run. The package is structured so additional app-server
capabilities can be added without coupling the helper to a particular project
management system.

The CLI uses [Cyclopts](https://cyclopts.readthedocs.io/) because typed
signatures and docstrings provide built-in help, shell completion, and
generated reference documentation with little boilerplate.

## Install

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Current command: start-task

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
uses `initialize`, `thread/start`, and `turn/start`; future commands can build
on the same client without changing the authentication or transport boundary.
