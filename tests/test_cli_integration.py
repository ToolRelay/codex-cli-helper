"""CLI integration coverage against the locally running Codex app-server."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest


DEFAULT_SOCKET = Path("/root/.codex/app-server-control/app-server-control.sock")


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


@pytest.mark.live
def test_start_queue_list_delete_task_against_live_app_server() -> None:
    """Create, queue a follow-up, observe, and delete one real Codex task.

    This test is deliberately opt-in because it creates a real durable Codex
    task and consumes a model turn. It never starts a second app-server.
    """

    if os.environ.get("CODEX_CLI_HELPER_LIVE") != "1":
        pytest.skip("set CODEX_CLI_HELPER_LIVE=1 to run against the local Codex daemon")

    socket_path = Path(
        os.environ.get("CODEX_APP_SERVER_SOCKET", str(DEFAULT_SOCKET))
    ).expanduser()
    if not socket_path.is_socket():
        pytest.skip(f"Codex app-server socket is not available: {socket_path}")

    repo_root = Path(__file__).parents[1]
    marker = f"codex-cli-helper live test {uuid.uuid4()}"
    title = f"Live task {uuid.uuid4()}"
    renamed_title = f"Renamed live task {uuid.uuid4()}"
    start = run_cli(
        repo_root,
        "start-task",
        "--cwd",
        str(repo_root.parent),
        "--socket",
        str(socket_path),
        "--title",
        title,
        "--effort",
        "high",
        "--prompt",
        f"{marker}. Do not modify files or use tools; reply with a short confirmation.",
        "--json",
    )
    started = json.loads(start.stdout)
    thread_id = started["threadId"]
    assert started["title"] == title
    assert isinstance(started["model"], str) and started["model"]
    assert started["effort"] == "high"

    try:
        matching: list[dict[str, object]] = []
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            listed = run_cli(
                repo_root,
                "list-tasks",
                "--cwd",
                str(repo_root.parent),
                "--socket",
                str(socket_path),
                "--json",
            )
            page = json.loads(listed.stdout)
            matching = [task for task in page["tasks"] if task.get("id") == thread_id]
            if matching:
                break
            time.sleep(0.25)
        assert matching, f"newly created task {thread_id} was not returned by thread/list"
        assert matching[0].get("name") == title
        assert marker in (matching[0].get("preview") or "")

        renamed = run_cli(
            repo_root,
            "rename-task",
            "--thread-id",
            thread_id,
            "--socket",
            str(socket_path),
            "--title",
            renamed_title,
            "--json",
        )
        assert json.loads(renamed.stdout) == {
            "threadId": thread_id,
            "title": renamed_title,
        }

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            listed = run_cli(
                repo_root,
                "list-tasks",
                "--cwd",
                str(repo_root.parent),
                "--socket",
                str(socket_path),
                "--json",
            )
            page = json.loads(listed.stdout)
            matching = [task for task in page["tasks"] if task.get("id") == thread_id]
            if matching and matching[0].get("name") == renamed_title:
                break
            time.sleep(0.25)
        assert matching and matching[0].get("name") == renamed_title

        queued = run_cli(
            repo_root,
            "queue-message",
            "--thread-id",
            thread_id,
            "--socket",
            str(socket_path),
            "--message",
            f"{marker}. Confirm receipt without modifying files or using tools.",
            "--json",
        )
        queue_result = json.loads(queued.stdout)
        assert queue_result["threadId"] == thread_id
        assert queue_result["queuedSubmissionId"]
        assert queue_result["previousStatus"] in {"idle", "active", "notLoaded"}
    finally:
        deleted = run_cli(
            repo_root,
            "delete-task",
            "--thread-id",
            thread_id,
            "--socket",
            str(socket_path),
            "--yes",
            "--json",
        )
        assert json.loads(deleted.stdout) == {
            "deleted": True,
            "threadId": thread_id,
        }


def test_install_bundled_skill_via_cli(tmp_path: Path) -> None:
    repo_root = Path(__file__).parents[1]
    skills_dir = tmp_path / "skills"
    installed = run_cli(
        repo_root,
        "install-skill",
        "--directory",
        str(skills_dir),
        "--json",
    )
    result = json.loads(installed.stdout)
    skill_dir = skills_dir / "codex-cli-helper"
    assert result["path"] == str(skill_dir)
    assert (skill_dir / "SKILL.md").is_file()
    assert (skill_dir / "agents" / "openai.yaml").is_file()
    assert "codex-cli-helper" in (skill_dir / "SKILL.md").read_text(encoding="utf-8")
