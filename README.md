# codex-cli-helper

A small, local Python command-line toolkit for working with the Codex
app-server. It is intentionally a thin protocol adapter: commands expose
Codex capabilities in a scriptable form while callers retain ownership of
workflow policy, scheduling, and project decisions.

The CLI provides a focused task lifecycle surface: `start-task` creates a
durable thread, gives it a user-facing title, and starts its first turn;
`rename-task` changes that title; `queue-message` sends a follow-up to an
existing thread; `list-tasks` reads task summaries; `delete-task` permanently
removes a task; and `install-skill` copies the bundled Codex skill into a
selected skills directory. The package is structured so additional app-server
capabilities can be added without coupling the helper to a particular project
management system.

The CLI uses [Cyclopts](https://cyclopts.readthedocs.io/) because typed
signatures and docstrings provide built-in help, shell completion, and
generated reference documentation with little boilerplate.

## Install

For development, install an editable package in an isolated environment:

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

For normal use, download the executable for your operating system from the
repository's GitHub Release and put it on your `PATH`. For example, on
Linux x86-64:

```bash
mkdir -p ~/.local/bin
curl -fL \
  https://github.com/ToolRelay/codex-cli-helper/releases/latest/download/codex-cli-helper-linux-x86_64 \
  -o ~/.local/bin/codex-cli-helper
chmod +x ~/.local/bin/codex-cli-helper
```

The release executable contains the Python runtime and application
dependencies; Python and a virtual environment are not required on the target
machine. Release assets are built independently for Linux x86-64, Linux
ARM64, macOS Intel, macOS Apple Silicon, and Windows x86-64. Verify the
matching `.sha256` file before installing when integrity verification is
required.

## Task lifecycle commands

### Start a task

```bash
codex-cli-helper start-task \
  --cwd /path/to/project \
  --title 'Implement the feature' \
  --prompt 'Work on the requested task and leave the result ready for review.'
```

By default, task creation inherits the active Codex configuration for the
model, reasoning effort, sandbox, approval policy, provider fallback, and the
current user's conventional app-server socket. Use an option only for a
one-task override:

```bash
codex-cli-helper start-task \
  --cwd /path/to/project \
  --title 'Investigate the API' \
  --model gpt-5.6-sol \
  --effort high \
  --sandbox workspace-write \
  --approval-policy on-request \
  --prompt 'Investigate and implement the requested change.'
```

Use `--json` for scripting:

```bash
codex-cli-helper start-task --cwd /path/to/project --title 'Short title' --prompt '...' --json
```

### Rename a task

```bash
codex-cli-helper rename-task \
  --thread-id THREAD_ID \
  --title 'A concise user-facing title'
```

The title is stored by the app-server and appears in task lists and the Codex
UI. Renaming does not start or resume a turn.

### List tasks

```bash
codex-cli-helper list-tasks --cwd /path/to/project
codex-cli-helper list-tasks --include-non-interactive --json
```

By default, `list-tasks` returns active (non-archived) tasks. Use
`--archived archived` to list archived tasks, `--source-kind` to select one or
more protocol source kinds, and `--cursor` to continue a paginated response.

### Queue a follow-up message

```bash
codex-cli-helper queue-message \
  --thread-id THREAD_ID \
  --message 'Please create or update the pull request and report its URL.'
```

The command reads the task status through the app-server. If the task is
`notLoaded`, it resumes the thread without starting a turn, then queues the
message. If it is already loaded, it queues directly. This means the command
works consistently for both persisted and in-memory tasks.

Omit the optional `--model` and `--effort` flags to preserve the thread's
stored settings. When supplied, the helper applies those settings before it
submits the message, so the queued turn uses the requested model and reasoning
effort:

```bash
codex-cli-helper queue-message \
  --thread-id THREAD_ID \
  --model gpt-5.6-sol \
  --effort high \
  --message 'Continue with the review feedback.' \
  --json
```

### Delete a task

```bash
codex-cli-helper delete-task --thread-id THREAD_ID --yes
```

Deletion is permanent, so `--yes` is required. Add `--json` when the result is
being consumed by another program.

### Install the bundled skill

```bash
codex-cli-helper install-skill --directory /root/.agents/skills
```

This creates `/root/.agents/skills/codex-cli-helper` containing the packaged
`SKILL.md` and UI metadata. Use `--force` to replace an existing copy when
updating the skill. The command does not contact the app-server.

The default socket is resolved from `$CODEX_HOME` when set, otherwise from
`~/.codex/app-server-control/app-server-control.sock`. Override it with
`--socket` when the daemon uses another Unix socket. The initialization
handshake uses the local daemon's existing Codex login; no API key is stored or
passed by this tool.

`--cwd` is simply the directory in which Codex should operate. The helper does
not impose project layout, branching, or workflow policy.

### Live daemon integration test

The lifecycle integration test uses the already-running local Codex app-server;
it never starts a second daemon. Run it explicitly because it creates and then
deletes a real task and consumes a model turn:

```bash
CODEX_CLI_HELPER_LIVE=1 python -m pytest -q -m live
```

The release workflow runs `-m "not live"` and therefore does not contact a
developer's daemon or require Codex authentication.

## Generated documentation

```bash
PYTHONPATH=src cyclopts generate-docs src/codex_cli_helper/cli.py \
  --output docs/cli.md --usage-name codex-cli-helper
```

## Releases

Commits merged to `main` use the Conventional Commits format. The release
workflow runs tests, uses Python Semantic Release to determine the next SemVer
version, updates `pyproject.toml` and the changelog, creates a `v<version>`
tag and GitHub Release, then attaches the platform executables and checksums.

Examples:

```text
fix: handle a closed app-server connection       # patch release
feat: add task archival                          # minor release
feat!: change the task output contract           # major release
```

The development install is intentionally separate from release installation:
the former is for editing and testing source, while the latter is a portable
single-file executable suitable for placing in a global `bin` directory.

## Design scope

This targets the Codex app-server protocol shipped with the local CLI. The
protocol is version-sensitive, so errors are surfaced instead of silently
falling back to a different model or transport. The current implementation
uses `initialize`, `thread/start`, `thread/name/set`, `thread/read`, `thread/resume`,
`thread/settings/update`, `thread/queue/add`, `turn/start`, `thread/list`, and
`thread/delete`; future commands can build on the same client without changing
the authentication or transport boundary.
