"""Command-line entry point for the Codex app-server toolkit."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from importlib.resources import files as resource_files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Annotated, Literal

from cyclopts import App, Parameter

from codex_cli_helper import __version__
from codex_cli_helper.client import AppServerError, CodexAppServer


SourceKind = Literal[
    "cli",
    "vscode",
    "exec",
    "appServer",
    "subAgent",
    "subAgentReview",
    "subAgentCompact",
    "subAgentThreadSpawn",
    "subAgentOther",
    "unknown",
]
SortKey = Literal["created_at", "updated_at", "recency_at", "section_position"]
SortDirection = Literal["asc", "desc"]
ReasoningEffort = Literal["low", "medium", "high", "xhigh", "max", "ultra"]
ALL_SOURCE_KINDS: tuple[SourceKind, ...] = (
    "cli",
    "vscode",
    "exec",
    "appServer",
    "subAgent",
    "subAgentReview",
    "subAgentCompact",
    "subAgentThreadSpawn",
    "subAgentOther",
    "unknown",
)
SKILL_NAME = "codex-cli-helper"


app = App(
    name="codex-cli-helper",
    version=__version__,
    help="Scriptable local tools for the Codex app-server.",
)


@app.command
def start_task(
    *,
    cwd: Annotated[
        Path,
        Parameter(name="--cwd", help="Absolute working directory for the new task."),
    ],
    prompt: Annotated[
        str,
        Parameter(name="--prompt", help="Initial task prompt sent to Codex."),
    ],
    socket_path: Annotated[
        Path,
        Parameter(
            name="--socket",
            help="Unix socket exposed by the running Codex app-server daemon.",
        ),
    ] = Path("/root/.codex/app-server-control/app-server-control.sock"),
    model: Annotated[str, Parameter(help="Exact Codex model to use.")] = "gpt-5.6-sol",
    sandbox: Literal["read-only", "workspace-write", "danger-full-access"] = "danger-full-access",
    approval_policy: Literal["untrusted", "on-request", "never"] = "never",
    thread_source: Annotated[str, Parameter(help="Analytics/source classification for the thread.")] = "toolrelay",
    session_start_source: Literal["startup", "clear"] = "startup",
    history_mode: Literal["legacy", "paginated"] = "paginated",
    runtime_workspace_root: Annotated[
        tuple[Path, ...],
        Parameter(
            name="--runtime-workspace-root",
            negative_iterable=(),
            help="Runtime workspace root; repeat for additional roots (defaults to --cwd).",
        ),
    ] = (),
    model_provider: Annotated[str | None, Parameter(help="Optional model provider identifier.")] = None,
    allow_provider_model_fallback: bool = False,
    timeout: Annotated[float, Parameter(help="Seconds to wait for socket responses.")] = 30.0,
    json_output: Annotated[
        bool,
        Parameter(name="--json", help="Print machine-readable JSON instead of human text."),
    ] = False,
) -> None:
    """Create a durable Codex thread and start its first turn.

    The command performs the app-server initialization handshake, so it uses the
    daemon's existing local Codex authentication. It never stores or asks for an
    API key. The task continues in the daemon after this process exits.

    Parameters
    ----------
    cwd:
        Absolute project directory where the task should run.
    prompt:
        Complete initial instructions for the task.
    """

    cwd = cwd.expanduser().resolve()
    if not cwd.is_dir():
        raise SystemExit(f"error: --cwd is not an existing directory: {cwd}")
    roots = [path.expanduser().resolve() for path in (runtime_workspace_root or (cwd,))]
    if any(not path.is_absolute() for path in roots):
        raise SystemExit("error: runtime workspace roots must be absolute paths")

    try:
        with CodexAppServer(socket_path.expanduser(), timeout=timeout) as client:
            task = client.start_task(
                cwd=cwd,
                prompt=prompt,
                model=model,
                sandbox=sandbox,
                approval_policy=approval_policy,
                thread_source=thread_source,
                session_start_source=session_start_source,
                history_mode=history_mode,
                runtime_workspace_roots=roots,
                model_provider=model_provider,
                allow_provider_model_fallback=allow_provider_model_fallback,
            )
    except AppServerError as exc:
        raise SystemExit(f"error: {exc}") from exc

    if json_output:
        print(json.dumps(task.as_dict(), sort_keys=True))
    else:
        print(f"Created Codex task {task.thread_id}")
        print(f"Turn: {task.turn_id or 'not returned'}")
        print(f"Model: {task.model}")
        print(f"Working directory: {task.cwd}")


@app.command
def list_tasks(
    *,
    socket_path: Annotated[
        Path,
        Parameter(
            name="--socket",
            help="Unix socket exposed by the running Codex app-server daemon.",
        ),
    ] = Path("/root/.codex/app-server-control/app-server-control.sock"),
    limit: Annotated[int, Parameter(help="Maximum number of tasks to return.")] = 100,
    cursor: Annotated[str | None, Parameter(help="Continue from a cursor returned by a previous page.")] = None,
    cwd: Annotated[Path | None, Parameter(help="Only return tasks whose working directory matches this path.")] = None,
    archived: Literal["active", "archived"] = "active",
    search_term: Annotated[str | None, Parameter(help="Search task names and previews.")] = None,
    project_id: Annotated[str | None, Parameter(help="Filter by Codex project identifier.")] = None,
    section_id: Annotated[str | None, Parameter(help="Filter by project section identifier.")] = None,
    parent_thread_id: Annotated[str | None, Parameter(help="Filter to direct child tasks of this thread.")] = None,
    ancestor_thread_id: Annotated[str | None, Parameter(help="Filter to descendants of this thread.")] = None,
    sort_key: SortKey | None = None,
    sort_direction: SortDirection | None = None,
    source_kind: Annotated[
        tuple[SourceKind, ...],
        Parameter(
            name="--source-kind",
            negative_iterable=(),
            help="Filter by source kind; repeat for multiple kinds.",
        ),
    ] = (),
    include_non_interactive: Annotated[
        bool,
        Parameter(help="Include exec and other non-interactive task sources."),
    ] = False,
    state_db_only: Annotated[
        bool,
        Parameter(help="Read only the app-server state database."),
    ] = False,
    timeout: Annotated[float, Parameter(help="Seconds to wait for socket responses.")] = 30.0,
    json_output: Annotated[
        bool,
        Parameter(name="--json", help="Print machine-readable JSON instead of human text."),
    ] = False,
) -> None:
    """List durable Codex tasks known to the app-server."""

    if limit < 1:
        raise SystemExit("error: --limit must be at least 1")
    if parent_thread_id and ancestor_thread_id:
        raise SystemExit("error: --parent-thread-id and --ancestor-thread-id cannot be combined")
    if source_kind and include_non_interactive:
        raise SystemExit("error: --source-kind cannot be combined with --include-non-interactive")
    cwd_filter = cwd.expanduser().resolve() if cwd is not None else None
    sources = list(ALL_SOURCE_KINDS if include_non_interactive else source_kind) or None

    try:
        with CodexAppServer(socket_path.expanduser(), timeout=timeout) as client:
            page = client.list_tasks(
                limit=limit,
                cursor=cursor,
                cwd=cwd_filter,
                archived=archived == "archived",
                search_term=search_term,
                project_id=project_id,
                section_id=section_id,
                parent_thread_id=parent_thread_id,
                ancestor_thread_id=ancestor_thread_id,
                sort_key=sort_key,
                sort_direction=sort_direction,
                source_kinds=sources,
                use_state_db_only=state_db_only,
            )
    except AppServerError as exc:
        raise SystemExit(f"error: {exc}") from exc

    if json_output:
        print(json.dumps(page.as_dict(), sort_keys=True))
        return
    if not page.data:
        print("No tasks found.")
    for task in page.data:
        task_id = task.get("id", "<unknown>")
        status = task.get("status")
        if isinstance(status, dict):
            status_text = status.get("type", "unknown")
        else:
            status_text = status or "unknown"
        label = task.get("name") or task.get("preview") or "(unnamed)"
        label = " ".join(str(label).split())
        if len(label) > 72:
            label = label[:69] + "..."
        print(f"{task_id}\t{status_text}\t{label}")
    if page.next_cursor:
        print(f"Next cursor: {page.next_cursor}")


@app.command
def delete_task(
    *,
    thread_id: Annotated[str, Parameter(name="--thread-id", help="Identifier of the task to delete.")],
    socket_path: Annotated[
        Path,
        Parameter(
            name="--socket",
            help="Unix socket exposed by the running Codex app-server daemon.",
        ),
    ] = Path("/root/.codex/app-server-control/app-server-control.sock"),
    yes: Annotated[
        bool,
        Parameter(name="--yes", help="Confirm permanent deletion."),
    ] = False,
    timeout: Annotated[float, Parameter(help="Seconds to wait for socket responses.")] = 30.0,
    json_output: Annotated[
        bool,
        Parameter(name="--json", help="Print machine-readable JSON instead of human text."),
    ] = False,
) -> None:
    """Permanently delete a durable Codex task through the app-server."""

    if not yes:
        raise SystemExit("error: deletion is permanent; pass --yes to confirm")
    try:
        with CodexAppServer(socket_path.expanduser(), timeout=timeout) as client:
            result = client.delete_task(thread_id)
    except AppServerError as exc:
        raise SystemExit(f"error: {exc}") from exc

    if json_output:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"Deleted Codex task {thread_id}")


@app.command
def queue_message(
    *,
    thread_id: Annotated[
        str,
        Parameter(name="--thread-id", help="Identifier of the existing Codex task."),
    ],
    message: Annotated[
        str,
        Parameter(name="--message", help="User message to append to the task queue."),
    ],
    socket_path: Annotated[
        Path,
        Parameter(
            name="--socket",
            help="Unix socket exposed by the running Codex app-server daemon.",
        ),
    ] = Path("/root/.codex/app-server-control/app-server-control.sock"),
    model: Annotated[
        str | None,
        Parameter(help="Optional model override for this and subsequent task turns."),
    ] = None,
    effort: Annotated[
        ReasoningEffort | None,
        Parameter(help="Optional reasoning-effort override for this and subsequent task turns."),
    ] = None,
    timeout: Annotated[float, Parameter(help="Seconds to wait for socket responses.")] = 30.0,
    json_output: Annotated[
        bool,
        Parameter(name="--json", help="Print machine-readable JSON instead of human text."),
    ] = False,
) -> None:
    """Load an existing task if needed, then queue one follow-up message.

    An unloaded task is resumed without starting a turn before the message is
    queued. Omitting ``--model`` and ``--effort`` preserves persisted settings;
    supplied overrides are applied before the queued turn can run.
    """

    if not message.strip():
        raise SystemExit("error: --message must not be empty")
    try:
        with CodexAppServer(socket_path.expanduser(), timeout=timeout) as client:
            result = client.queue_message(
                thread_id=thread_id,
                message=message,
                model=model,
                effort=effort,
            )
    except AppServerError as exc:
        raise SystemExit(f"error: {exc}") from exc

    if json_output:
        print(json.dumps(result.as_dict(), sort_keys=True))
        return
    print(f"Queued message {result.queued_submission_id} for Codex task {result.thread_id}")
    print(f"Previous status: {result.previous_status}")
    print(f"Resumed before queueing: {'yes' if result.resumed else 'no'}")
    if result.model is not None:
        print(f"Model: {result.model}")
    if result.effort is not None:
        print(f"Reasoning effort: {result.effort}")


def _copy_resource_tree(source: Traversable, destination: Path) -> None:
    """Copy an importlib.resources tree into a filesystem directory."""

    destination.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        target = destination / child.name
        if child.is_dir():
            _copy_resource_tree(child, target)
        else:
            target.write_bytes(child.read_bytes())


@app.command
def install_skill(
    *,
    directory: Annotated[
        Path,
        Parameter(
            name="--directory",
            help="Parent directory in which to install the bundled skill.",
        ),
    ],
    force: Annotated[
        bool,
        Parameter(help="Replace an existing codex-cli-helper skill directory."),
    ] = False,
    json_output: Annotated[
        bool,
        Parameter(name="--json", help="Print machine-readable JSON instead of human text."),
    ] = False,
) -> None:
    """Install the bundled Codex skill under a selected skills directory."""

    directory = directory.expanduser().resolve()
    destination = directory / SKILL_NAME
    if destination.exists() and not force:
        raise SystemExit(
            f"error: skill already exists at {destination}; pass --force to replace it"
        )
    try:
        directory.mkdir(parents=True, exist_ok=True)
        if not directory.is_dir():
            raise SystemExit(f"error: --directory is not a directory: {directory}")
        source = resource_files("codex_cli_helper").joinpath("skill")
        if not source.is_dir():
            raise SystemExit("error: bundled codex-cli-helper skill is unavailable")
        with tempfile.TemporaryDirectory(prefix=f".{SKILL_NAME}.", dir=directory) as temp_dir:
            staged = Path(temp_dir) / SKILL_NAME
            _copy_resource_tree(source, staged)
            if destination.exists() or destination.is_symlink():
                if destination.is_symlink() or not destination.is_dir():
                    destination.unlink()
                else:
                    shutil.rmtree(destination)
            os.replace(staged, destination)
    except OSError as exc:
        raise SystemExit(f"error: could not install skill at {destination}: {exc}") from exc

    result = {"skill": SKILL_NAME, "directory": str(directory), "path": str(destination)}
    if json_output:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"Installed {SKILL_NAME} skill at {destination}")


if __name__ == "__main__":
    app()
