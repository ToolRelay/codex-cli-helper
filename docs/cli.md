# codex-cli-helper

```console
codex-cli-helper COMMAND
```

Start durable, visible Codex app-server tasks from a local CLI.

## Table of Contents

- [`start-task`](#codex-cli-helper-start-task)

**Commands**:

* [`start-task`](#codex-cli-helper-start-task): Create a durable Codex thread and start its first turn.

## codex-cli-helper start-task

```console
codex-cli-helper start-task --cwd PATH --prompt STR [OPTIONS]
```

Create a durable Codex thread and start its first turn.

The command performs the app-server initialization handshake, so it uses the
daemon's existing local Codex authentication. It never stores or asks for an
API key. The task continues in the daemon after this process exits.

**Parameters**:

* `--cwd`: Absolute working directory for the new task. **[required]**
* `--prompt`: Initial task prompt sent to Codex. **[required]**
* `--socket`: Unix socket exposed by the running Codex app-server daemon. *[default: /root/.codex/app-server-control/app-server-control.sock]*
* `--model`: Exact Codex model to use. *[default: gpt-5.6-sol]*
* `--sandbox`: *[choices: read-only, workspace-write, danger-full-access]* *[default: danger-full-access]*
* `--approval-policy`: *[choices: untrusted, on-request, never]* *[default: never]*
* `--thread-source`: Analytics/source classification for the thread. *[default: toolrelay]*
* `--session-start-source`: *[choices: startup, clear]* *[default: startup]*
* `--history-mode`: *[choices: legacy, paginated]* *[default: paginated]*
* `--runtime-workspace-root`: Runtime workspace root; repeat for additional roots (defaults to --cwd). *[default: ()]*
* `--model-provider`: Optional model provider identifier.
* `--allow-provider-model-fallback, --no-allow-provider-model-fallback`: *[default: False]*
* `--timeout`: Seconds to wait for socket responses. *[default: 30.0]*
* `--json, --no-json`: Print machine-readable JSON instead of human text. *[default: False]*
