"""Command-line entry point for the Codex app-server toolkit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

from cyclopts import App, Parameter

from codex_cli_helper import __version__
from codex_cli_helper.client import AppServerError, CodexAppServer


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


if __name__ == "__main__":
    app()
