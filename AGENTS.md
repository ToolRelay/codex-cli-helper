# Codex CLI Helper

This private ToolRelay repository contains a deliberately thin Python CLI for
starting durable Codex app-server tasks on the local machine. It is an adapter
around the installed Codex daemon, not a replacement orchestrator.

## Boundaries

- Keep the CLI focused on creating a thread and starting its first turn.
- Use the local Unix app-server socket and the daemon's existing authentication; never embed API keys or credentials.
- Do not add GitHub, Outline, Project-state, scheduler, or SQLite orchestration logic here.
- Preserve exact user-supplied model and workspace settings; do not silently fall back.
- New task code must remain compatible with isolated Git worktrees and must not modify a caller's repository.

## Development

Use Python 3.11+ and the project environment. Run `pytest`, `python -m codex_cli_helper --help`, and regenerate the CLI documentation before committing. Keep generated docs synchronized with the typed command signature.
