"""End-to-end CLI coverage against a fake app-server Unix socket."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest
from websockets.sync.server import ServerConnection, unix_serve


@pytest.fixture
def fake_app_server(tmp_path: Path):
    socket_path = tmp_path / "app-server.sock"
    state: dict[str, dict[str, Any]] = {}
    lock = threading.Lock()
    counter = 0

    def send(connection: ServerConnection, request_id: Any, result: dict[str, Any]) -> None:
        connection.send(json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}))

    def handler(connection: ServerConnection) -> None:
        nonlocal counter
        try:
            for raw in connection:
                request = json.loads(raw)
                method = request.get("method")
                request_id = request.get("id")
                params = request.get("params") or {}
                if method == "initialize":
                    send(connection, request_id, {"userAgent": "fake-codex"})
                elif method == "initialized":
                    continue
                elif method == "thread/start":
                    with lock:
                        counter += 1
                        thread_id = f"thread-{counter}"
                        state[thread_id] = {
                            "id": thread_id,
                            "name": "Integration task",
                            "cwd": params["cwd"],
                            "model": params["model"],
                            "status": {"type": "active", "activeFlags": []},
                            "archived": False,
                            "source": "cli",
                        }
                        task = dict(state[thread_id])
                    send(connection, request_id, {"thread": task})
                elif method == "turn/start":
                    send(connection, request_id, {"turn": {"id": "turn-1"}})
                elif method == "thread/list":
                    with lock:
                        tasks = list(state.values())
                    if params.get("archived") is True:
                        tasks = [task for task in tasks if task.get("archived") is True]
                    else:
                        tasks = [task for task in tasks if task.get("archived") is not True]
                    if params.get("cwd"):
                        tasks = [task for task in tasks if task.get("cwd") == params["cwd"]]
                    send(connection, request_id, {"data": tasks, "nextCursor": None, "backwardsCursor": None})
                elif method == "thread/delete":
                    thread_id = params["threadId"]
                    with lock:
                        state.pop(thread_id, None)
                    send(connection, request_id, {})
                else:
                    send(connection, request_id, {"ok": True})
        except (OSError, json.JSONDecodeError):
            # The client may close its side immediately after receiving a response.
            return

    server = unix_serve(handler, socket_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield socket_path, state
    finally:
        server.shutdown()
        thread.join(timeout=5)


def run_cli(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    return subprocess.run(
        [sys.executable, "-m", "codex_cli_helper", *args],
        cwd=repo_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def test_start_list_delete_task_via_cli(tmp_path: Path, fake_app_server: tuple[Path, dict[str, Any]]) -> None:
    socket_path, state = fake_app_server
    repo_root = Path(__file__).parents[1]
    start = run_cli(
        repo_root,
        "start-task",
        "--cwd",
        str(tmp_path),
        "--socket",
        str(socket_path),
        "--prompt",
        "integration task",
        "--json",
    )
    started = json.loads(start.stdout)
    assert started["threadId"] in state

    listed = run_cli(
        repo_root,
        "list-tasks",
        "--cwd",
        str(tmp_path),
        "--socket",
        str(socket_path),
        "--json",
    )
    page = json.loads(listed.stdout)
    assert [task["id"] for task in page["tasks"]] == [started["threadId"]]

    deleted = run_cli(
        repo_root,
        "delete-task",
        "--thread-id",
        started["threadId"],
        "--socket",
        str(socket_path),
        "--yes",
        "--json",
    )
    assert json.loads(deleted.stdout) == {"deleted": True, "threadId": started["threadId"]}

    listed_again = run_cli(
        repo_root,
        "list-tasks",
        "--cwd",
        str(tmp_path),
        "--socket",
        str(socket_path),
        "--json",
    )
    assert json.loads(listed_again.stdout)["tasks"] == []
