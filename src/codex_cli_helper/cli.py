"""Command-line entry point for the Codex app-server toolkit."""

from __future__ import annotations

import json
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


if __name__ == "__main__":
    app()
