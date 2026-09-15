from pathlib import Path

from codex_cli_helper.client import CodexAppServer, StartedTask


def test_started_task_json_shape() -> None:
    task = StartedTask("thread-1", "turn-1", "/workspace", "gpt-5.6-sol")
    assert task.as_dict() == {
        "threadId": "thread-1",
        "turnId": "turn-1",
        "cwd": "/workspace",
        "model": "gpt-5.6-sol",
    }


def test_queue_message_resumes_an_unloaded_thread_before_queueing() -> None:
    client = CodexAppServer(Path("/tmp/codex.sock"))
    calls: list[tuple[str, dict[str, object]]] = []

    def request(method: str, params: dict[str, object]) -> dict[str, object]:
        calls.append((method, params))
        if method == "thread/read":
            return {
                "thread": {
                    "id": "thread-1",
                    "status": {"type": "notLoaded"},
                    "model": "gpt-5.6-sol",
                    "reasoningEffort": "medium",
                }
            }
        if method == "thread/resume":
            return {
                "thread": {
                    "id": "thread-1",
                    "status": {"type": "idle"},
                    "model": "gpt-5.6-sol",
                    "reasoningEffort": "medium",
                }
            }
        if method == "thread/queue/add":
            return {"queuedSubmission": {"id": "submission-1"}}
        raise AssertionError(f"unexpected method: {method}")

    client._request = request  # type: ignore[method-assign]
    result = client.queue_message(
        thread_id="thread-1",
        message="continue the task",
        model=None,
        effort=None,
    )

    assert [method for method, _ in calls] == [
        "thread/read",
        "thread/resume",
        "thread/queue/add",
    ]
    assert calls[1][1] == {"threadId": "thread-1", "excludeTurns": True}
    assert calls[2][1]["threadId"] == "thread-1"
    assert calls[2][1]["input"] == [{"type": "text", "text": "continue the task"}]
    assert result.as_dict() == {
        "threadId": "thread-1",
        "queuedSubmissionId": "submission-1",
        "previousStatus": "notLoaded",
        "resumed": True,
        "model": "gpt-5.6-sol",
        "effort": "medium",
        "settingsUpdated": False,
    }


def test_queue_message_updates_loaded_thread_settings_before_queueing() -> None:
    client = CodexAppServer(Path("/tmp/codex.sock"))
    calls: list[tuple[str, dict[str, object]]] = []

    def request(method: str, params: dict[str, object]) -> dict[str, object]:
        calls.append((method, params))
        if method == "thread/read":
            return {
                "thread": {
                    "id": "thread-1",
                    "status": {"type": "idle"},
                    "model": "gpt-5.6-sol",
                    "reasoningEffort": "medium",
                }
            }
        if method == "thread/settings/update":
            return {}
        if method == "thread/queue/add":
            return {"queuedSubmission": {"id": "submission-1"}}
        raise AssertionError(f"unexpected method: {method}")

    client._request = request  # type: ignore[method-assign]
    client._wait_for_notification = lambda *_args: {  # type: ignore[method-assign]
        "method": "thread/settings/updated",
        "params": {"threadId": "thread-1"},
    }
    result = client.queue_message(
        thread_id="thread-1",
        message="continue the task",
        model="gpt-5.6-luna",
        effort="high",
    )

    assert [method for method, _ in calls] == [
        "thread/read",
        "thread/settings/update",
        "thread/queue/add",
    ]
    assert calls[1][1] == {
        "threadId": "thread-1",
        "model": "gpt-5.6-luna",
        "effort": "high",
    }
    assert result.model == "gpt-5.6-luna"
    assert result.effort == "high"
    assert result.settings_updated is True
