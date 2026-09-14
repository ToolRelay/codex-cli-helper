from codex_cli_helper.client import StartedTask


def test_started_task_json_shape() -> None:
    task = StartedTask("thread-1", "turn-1", "/workspace", "gpt-5.6-sol")
    assert task.as_dict() == {
        "threadId": "thread-1",
        "turnId": "turn-1",
        "cwd": "/workspace",
        "model": "gpt-5.6-sol",
    }
