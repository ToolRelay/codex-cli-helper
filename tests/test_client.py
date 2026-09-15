from pathlib import Path

from pytest import MonkeyPatch

from codex_cli_helper.client import CodexAppServer, StartedTask
from codex_cli_helper.cli import default_socket_path


def test_started_task_json_shape() -> None:
    task = StartedTask("thread-1", "turn-1", "/workspace", "Implement the feature", "gpt-5.6-sol", "medium")
    assert task.as_dict() == {
        "threadId": "thread-1",
        "turnId": "turn-1",
        "cwd": "/workspace",
        "title": "Implement the feature",
        "model": "gpt-5.6-sol",
        "effort": "medium",
    }


def test_default_socket_path_uses_codex_home_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", "/custom/codex-home")
    assert default_socket_path() == Path(
        "/custom/codex-home/app-server-control/app-server-control.sock"
    )


def test_start_task_omits_unset_configuration_overrides() -> None:
    client = CodexAppServer(Path("/tmp/codex.sock"))
    calls: list[tuple[str, dict[str, object]]] = []

    def request(method: str, params: dict[str, object]) -> dict[str, object]:
        calls.append((method, params))
        if method == "thread/start":
            return {
                "thread": {
                    "id": "thread-1",
                    "model": "configured-model",
                    "reasoningEffort": "medium",
                }
            }
        if method == "thread/name/set":
            return {}
        if method == "turn/start":
            return {"turn": {"id": "turn-1"}}
        raise AssertionError(f"unexpected method: {method}")

    client._request = request  # type: ignore[method-assign]
    result = client.start_task(
        cwd=Path("/workspace"),
        title="Do the work",
        prompt="do the work",
        model=None,
        effort=None,
        sandbox=None,
        approval_policy=None,
        thread_source="toolrelay",
        session_start_source="startup",
        history_mode="paginated",
        runtime_workspace_roots=[Path("/workspace")],
        model_provider=None,
        allow_provider_model_fallback=None,
    )

    assert [method for method, _ in calls] == ["thread/start", "thread/name/set", "turn/start"]
    assert calls[0][1] == {
        "cwd": "/workspace",
        "runtimeWorkspaceRoots": ["/workspace"],
        "threadSource": "toolrelay",
        "sessionStartSource": "startup",
        "historyMode": "paginated",
    }
    assert calls[1][1] == {"threadId": "thread-1", "name": "Do the work"}
    assert "model" not in calls[2][1]
    assert "approvalPolicy" not in calls[2][1]
    assert result.as_dict() == {
        "threadId": "thread-1",
        "turnId": "turn-1",
        "cwd": "/workspace",
        "title": "Do the work",
        "model": "configured-model",
        "effort": "medium",
    }


def test_start_task_applies_explicit_overrides_before_first_turn() -> None:
    client = CodexAppServer(Path("/tmp/codex.sock"))
    calls: list[tuple[str, dict[str, object]]] = []

    def request(method: str, params: dict[str, object]) -> dict[str, object]:
        calls.append((method, params))
        if method == "thread/start":
            return {
                "thread": {
                    "id": "thread-1",
                    "model": "gpt-5.6-sol",
                    "reasoningEffort": "medium",
                }
            }
        if method == "thread/name/set":
            return {}
        if method == "thread/settings/update":
            return {}
        if method == "turn/start":
            return {"turn": {"id": "turn-1"}}
        raise AssertionError(f"unexpected method: {method}")

    client._request = request  # type: ignore[method-assign]
    client._wait_for_notification = lambda *_args: {  # type: ignore[method-assign]
        "method": "thread/settings/updated",
        "params": {"threadId": "thread-1"},
    }
    result = client.start_task(
        cwd=Path("/workspace"),
        title="Do the work",
        prompt="do the work",
        model="gpt-5.6-sol",
        effort="high",
        sandbox="read-only",
        approval_policy="on-request",
        thread_source="toolrelay",
        session_start_source="startup",
        history_mode="paginated",
        runtime_workspace_roots=[Path("/workspace")],
        model_provider="openai",
        allow_provider_model_fallback=True,
    )

    assert [method for method, _ in calls] == [
        "thread/start",
        "thread/name/set",
        "thread/settings/update",
        "turn/start",
    ]
    assert calls[0][1] == {
        "cwd": "/workspace",
        "runtimeWorkspaceRoots": ["/workspace"],
        "threadSource": "toolrelay",
        "sessionStartSource": "startup",
        "historyMode": "paginated",
        "model": "gpt-5.6-sol",
        "sandbox": "read-only",
        "approvalPolicy": "on-request",
        "modelProvider": "openai",
        "allowProviderModelFallback": True,
    }
    assert calls[1][1] == {"threadId": "thread-1", "name": "Do the work"}
    assert calls[2][1] == {"threadId": "thread-1", "effort": "high"}
    assert calls[3][1]["model"] == "gpt-5.6-sol"
    assert calls[3][1]["approvalPolicy"] == "on-request"
    assert result.effort == "high"


def test_rename_task_sets_protocol_name() -> None:
    client = CodexAppServer(Path("/tmp/codex.sock"))
    calls: list[tuple[str, dict[str, object]]] = []

    def request(method: str, params: dict[str, object]) -> dict[str, object]:
        calls.append((method, params))
        return {}

    client._request = request  # type: ignore[method-assign]
    assert client.rename_task(thread_id="thread-1", title="A better title") == {
        "threadId": "thread-1",
        "title": "A better title",
    }
    assert calls == [("thread/name/set", {"threadId": "thread-1", "name": "A better title"})]


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
