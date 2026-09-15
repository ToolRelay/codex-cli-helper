---
name: codex-cli-helper
description: Use the local codex-cli-helper binary to create, queue, list, or delete durable Codex app-server tasks through the configured Unix socket.
---

# Codex CLI Helper

Use this skill when a workflow needs to manage Codex app-server tasks from a
shell or another script. The helper talks to the local app-server socket and
uses its existing authentication; do not look for credentials or manipulate
Codex's SQLite databases directly.

## Commands

Use the installed `codex-cli-helper` executable:

```bash
codex-cli-helper start-task --cwd PROJECT_DIR --prompt 'Complete the requested work.' --json
codex-cli-helper queue-message --thread-id THREAD_ID --message 'Continue with the review feedback.' --json
codex-cli-helper list-tasks --cwd PROJECT_DIR --json
codex-cli-helper delete-task --thread-id THREAD_ID --yes --json
```

Pass `--socket SOCKET_PATH` when the app-server does not use its default local
socket. Keep prompts complete and actionable; `start-task` creates a durable
thread and starts its first turn, then returns while the app-server continues
the task.

`list-tasks` returns active interactive tasks by default. Add
`--include-non-interactive` when exec or other non-interactive sources must be
included. Use the returned `threadId` with `delete-task` only when permanent
deletion has been explicitly requested; the command requires `--yes` as a
second guard.

`queue-message` reads task status first. For a `notLoaded` task it resumes the
thread without starting a turn, then queues the message; loaded tasks are
queued directly. Omit `--model` and `--effort` to preserve existing settings,
or provide either flag to apply it before the queued turn runs.

Prefer `--json` for automation and preserve the identifiers it returns. Treat
the app-server response as authoritative: surface errors instead of retrying
with a different socket, model, or transport.
