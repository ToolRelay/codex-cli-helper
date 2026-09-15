# codex-cli-helper

```console
codex-cli-helper COMMAND
```

Scriptable local tools for the Codex app-server.

## Table of Contents

- [`start-task`](#codex-cli-helper-start-task)
- [`list-tasks`](#codex-cli-helper-list-tasks)
- [`delete-task`](#codex-cli-helper-delete-task)
- [`queue-message`](#codex-cli-helper-queue-message)
- [`install-skill`](#codex-cli-helper-install-skill)

**Commands**:

* [`delete-task`](#codex-cli-helper-delete-task): Permanently delete a durable Codex task through the app-server.
* [`install-skill`](#codex-cli-helper-install-skill): Install the bundled Codex skill under a selected skills directory.
* [`list-tasks`](#codex-cli-helper-list-tasks): List durable Codex tasks known to the app-server.
* [`queue-message`](#codex-cli-helper-queue-message): Load an existing task if needed, then queue one follow-up message.
* [`start-task`](#codex-cli-helper-start-task): Create a durable Codex thread and start its first turn.

## codex-cli-helper start-task

```console
codex-cli-helper start-task --cwd PATH --prompt STR [OPTIONS]
```

Create a durable Codex thread and start its first turn.

The command performs the app-server initialization handshake, so it uses the
daemon's existing local Codex authentication. It never stores or asks for an
API key. Model, effort, sandbox, and approval policy inherit the active
Codex configuration unless explicitly overridden. The task continues in the
daemon after this process exits.

**Parameters**:

* `--cwd`: Absolute working directory for the new task. **[required]**
* `--prompt`: Initial task prompt sent to Codex. **[required]**
* `--socket`: Unix socket exposed by the running Codex app-server daemon. *[default: /root/.codex/app-server-control/app-server-control.sock]*
* `--model`: Optional model override; omit to use the active Codex configuration.
* `--effort`: Optional reasoning-effort override; omit to use the active Codex configuration. *[choices: low, medium, high, xhigh, max, ultra]*
* `--sandbox`: Optional sandbox override; omit to use the active Codex configuration. *[choices: read-only, workspace-write, danger-full-access]*
* `--approval-policy`: Optional approval-policy override; omit to use the active Codex configuration. *[choices: untrusted, on-request, never]*
* `--thread-source`: Analytics/source classification for the thread. *[default: toolrelay]*
* `--session-start-source`: *[choices: startup, clear]* *[default: startup]*
* `--history-mode`: *[choices: legacy, paginated]* *[default: paginated]*
* `--runtime-workspace-root`: Runtime workspace root; repeat for additional roots (defaults to --cwd). *[default: ()]*
* `--model-provider`: Optional model provider identifier.
* `--allow-provider-model-fallback, --no-allow-provider-model-fallback`: Allow provider model fallback; omit to use the app-server default.
* `--timeout`: Seconds to wait for socket responses. *[default: 30.0]*
* `--json, --no-json`: Print machine-readable JSON instead of human text. *[default: False]*

## codex-cli-helper list-tasks

```console
codex-cli-helper list-tasks [OPTIONS]
```

List durable Codex tasks known to the app-server.

**Parameters**:

* `--socket`: Unix socket exposed by the running Codex app-server daemon. *[default: /root/.codex/app-server-control/app-server-control.sock]*
* `--limit`: Maximum number of tasks to return. *[default: 100]*
* `--cursor`: Continue from a cursor returned by a previous page.
* `--cwd`: Only return tasks whose working directory matches this path.
* `--archived`: *[choices: active, archived]* *[default: active]*
* `--search-term`: Search task names and previews.
* `--project-id`: Filter by Codex project identifier.
* `--section-id`: Filter by project section identifier.
* `--parent-thread-id`: Filter to direct child tasks of this thread.
* `--ancestor-thread-id`: Filter to descendants of this thread.
* `--sort-key`: *[choices: created_at, updated_at, recency_at, section_position]*
* `--sort-direction`: *[choices: asc, desc]*
* `--source-kind`: Filter by source kind; repeat for multiple kinds. *[choices: cli, vscode, exec, appServer, subAgent, subAgentReview, subAgentCompact, subAgentThreadSpawn, subAgentOther, unknown]* *[default: ()]*
* `--include-non-interactive, --no-include-non-interactive`: Include exec and other non-interactive task sources. *[default: False]*
* `--state-db-only, --no-state-db-only`: Read only the app-server state database. *[default: False]*
* `--timeout`: Seconds to wait for socket responses. *[default: 30.0]*
* `--json, --no-json`: Print machine-readable JSON instead of human text. *[default: False]*

## codex-cli-helper delete-task

```console
codex-cli-helper delete-task --thread-id STR [OPTIONS]
```

Permanently delete a durable Codex task through the app-server.

**Parameters**:

* `--thread-id`: Identifier of the task to delete. **[required]**
* `--socket`: Unix socket exposed by the running Codex app-server daemon. *[default: /root/.codex/app-server-control/app-server-control.sock]*
* `--yes, --no-yes`: Confirm permanent deletion. *[default: False]*
* `--timeout`: Seconds to wait for socket responses. *[default: 30.0]*
* `--json, --no-json`: Print machine-readable JSON instead of human text. *[default: False]*

## codex-cli-helper queue-message

```console
codex-cli-helper queue-message --thread-id STR --message STR [OPTIONS]
```

Load an existing task if needed, then queue one follow-up message.

An unloaded task is resumed without starting a turn before the message is
queued. Omitting ``--model`` and ``--effort`` preserves persisted settings;
supplied overrides are applied before the queued turn can run.

**Parameters**:

* `--thread-id`: Identifier of the existing Codex task. **[required]**
* `--message`: User message to append to the task queue. **[required]**
* `--socket`: Unix socket exposed by the running Codex app-server daemon. *[default: /root/.codex/app-server-control/app-server-control.sock]*
* `--model`: Optional model override for this and subsequent task turns.
* `--effort`: Optional reasoning-effort override for this and subsequent task turns. *[choices: low, medium, high, xhigh, max, ultra]*
* `--timeout`: Seconds to wait for socket responses. *[default: 30.0]*
* `--json, --no-json`: Print machine-readable JSON instead of human text. *[default: False]*

## codex-cli-helper install-skill

```console
codex-cli-helper install-skill --directory PATH [OPTIONS]
```

Install the bundled Codex skill under a selected skills directory.

**Parameters**:

* `--directory`: Parent directory in which to install the bundled skill. **[required]**
* `--force, --no-force`: Replace an existing codex-cli-helper skill directory. *[default: False]*
* `--json, --no-json`: Print machine-readable JSON instead of human text. *[default: False]*
