"""Minimal synchronous client for the local Codex app-server WebSocket."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from websockets.sync.client import ClientConnection, unix_connect


class AppServerError(RuntimeError):
    """The app-server rejected a request or returned an invalid response."""


@dataclass(frozen=True)
class StartedTask:
    """Identifiers and effective settings returned for a newly started task."""

    thread_id: str
    turn_id: str | None
    cwd: str
    title: str
    model: str | None
    effort: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "threadId": self.thread_id,
            "turnId": self.turn_id,
            "cwd": self.cwd,
            "title": self.title,
            "model": self.model,
            "effort": self.effort,
        }


@dataclass(frozen=True)
class ListedTasks:
    """A page of task summaries returned by the app-server."""

    data: list[dict[str, Any]]
    next_cursor: str | None = None
    backwards_cursor: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "tasks": self.data,
            "nextCursor": self.next_cursor,
            "backwardsCursor": self.backwards_cursor,
        }


@dataclass(frozen=True)
class QueuedMessage:
    """Result of loading a thread if required and queueing a user message."""

    thread_id: str
    queued_submission_id: str
    previous_status: str
    resumed: bool
    model: str | None
    effort: str | None
    settings_updated: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "threadId": self.thread_id,
            "queuedSubmissionId": self.queued_submission_id,
            "previousStatus": self.previous_status,
            "resumed": self.resumed,
            "model": self.model,
            "effort": self.effort,
            "settingsUpdated": self.settings_updated,
        }


class CodexAppServer:
    """Small JSON-RPC client that performs the Codex initialization handshake."""

    def __init__(self, socket_path: Path, *, timeout: float = 30.0) -> None:
        self.socket_path = socket_path
        self.timeout = timeout
        self._next_id = 1
        self._connection: ClientConnection | None = None
        self._notifications: list[dict[str, Any]] = []

    def __enter__(self) -> "CodexAppServer":
        try:
            self._connection = unix_connect(
                str(self.socket_path),
                open_timeout=self.timeout,
                close_timeout=self.timeout,
                # The Codex app-server doesn't negotiate permessage-deflate
                # on its Unix WebSocket listener and closes the handshake if
                # the extension is offered.
                compression=None,
            )
        except OSError as exc:
            raise AppServerError(
                f"could not connect to Codex app-server socket {self.socket_path}: {exc}"
            ) from exc
        self._request(
            "initialize",
            {
                "clientInfo": {
                    "name": "codex-cli-helper",
                    "version": "0.1.0",
                },
                "capabilities": {"experimentalApi": True},
            },
        )
        self._notify("initialized", {})
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _next_request_id(self) -> int:
        request_id = self._next_id
        self._next_id += 1
        return request_id

    def _send(self, message: dict[str, Any]) -> None:
        if self._connection is None:
            raise AppServerError("app-server connection is not open")
        self._connection.send(json.dumps(message, separators=(",", ":")))

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def _receive_message(self) -> dict[str, Any]:
        """Read and validate one JSON-RPC message from the app-server."""

        if self._connection is None:
            raise AppServerError("app-server connection is not open")
        try:
            raw = self._connection.recv(timeout=self.timeout)
        except TimeoutError as exc:
            raise AppServerError("timed out waiting for app-server response") from exc
        if raw is None:
            raise AppServerError("app-server closed the connection")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            message = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AppServerError("app-server returned invalid JSON") from exc
        if not isinstance(message, dict):
            raise AppServerError("app-server returned a non-object JSON-RPC message")
        return message

    def _save_notification(self, message: dict[str, Any]) -> None:
        if isinstance(message.get("method"), str):
            self._notifications.append(message)

    def _wait_for_notification(
        self,
        method: str,
        matches: Callable[[dict[str, Any]], bool],
    ) -> dict[str, Any]:
        """Wait for one notification while preserving unrelated notifications."""

        for index, message in enumerate(self._notifications):
            if message.get("method") == method and matches(message):
                return self._notifications.pop(index)
        while True:
            message = self._receive_message()
            if message.get("method") == method and matches(message):
                return message
            self._save_notification(message)

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self._next_request_id()
        self._send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
        )
        while True:
            try:
                message = self._receive_message()
            except AppServerError as exc:
                raise AppServerError(f"{method}: {exc}") from exc
            if message.get("id") != request_id:
                # Notifications and unrelated responses may be interleaved with a request.
                self._save_notification(message)
                continue
            if "error" in message:
                error = message["error"]
                detail = error.get("message", error) if isinstance(error, dict) else error
                raise AppServerError(f"{method} failed: {detail}")
            result = message.get("result")
            if not isinstance(result, dict):
                raise AppServerError(f"{method} returned no result")
            return result

    def start_task(
        self,
        *,
        cwd: Path,
        title: str,
        prompt: str,
        model: str | None,
        effort: str | None,
        sandbox: str | None,
        approval_policy: str | None,
        thread_source: str,
        session_start_source: str,
        history_mode: str,
        runtime_workspace_roots: list[Path],
        model_provider: str | None,
        allow_provider_model_fallback: bool | None,
    ) -> StartedTask:
        """Create a durable thread and start its first turn."""

        thread_params: dict[str, Any] = {
            "cwd": str(cwd),
            "runtimeWorkspaceRoots": [str(path) for path in runtime_workspace_roots],
            "threadSource": thread_source,
            "sessionStartSource": session_start_source,
            "historyMode": history_mode,
        }
        optional_thread_params = {
            "model": model,
            "allowProviderModelFallback": allow_provider_model_fallback,
            "sandbox": sandbox,
            "approvalPolicy": approval_policy,
            "modelProvider": model_provider,
        }
        thread_params.update(
            {key: value for key, value in optional_thread_params.items() if value is not None}
        )

        thread_result = self._request("thread/start", thread_params)
        thread = thread_result.get("thread")
        if not isinstance(thread, dict) or not isinstance(thread.get("id"), str):
            raise AppServerError("thread/start returned no thread id")
        thread_id = thread["id"]

        # Thread creation does not accept a user-facing title. Set it through
        # the same protocol method exposed by ``rename_task`` before starting
        # the first turn.
        self.rename_task(thread_id=thread_id, title=title)

        effective_model = thread.get("model")
        effective_effort = thread.get("reasoningEffort")
        if effective_model is not None and not isinstance(effective_model, str):
            raise AppServerError("thread/start returned an invalid model")
        if effective_effort is not None and not isinstance(effective_effort, str):
            raise AppServerError("thread/start returned an invalid reasoning effort")

        if effort is not None:
            self._request(
                "thread/settings/update",
                {"threadId": thread_id, "effort": effort},
            )
            self._wait_for_notification(
                "thread/settings/updated",
                lambda notification: isinstance(notification.get("params"), dict)
                and notification["params"].get("threadId") == thread_id,
            )
            effective_effort = effort

        turn_params: dict[str, Any] = {
            "threadId": thread_id,
            "clientUserMessageId": str(uuid.uuid4()),
            "input": [{"type": "text", "text": prompt}],
            "cwd": str(cwd),
            "runtimeWorkspaceRoots": [str(path) for path in runtime_workspace_roots],
        }
        if model is not None:
            turn_params["model"] = model
        if approval_policy is not None:
            turn_params["approvalPolicy"] = approval_policy
        turn_result = self._request("turn/start", turn_params)
        turn = turn_result.get("turn")
        turn_id = turn.get("id") if isinstance(turn, dict) else None
        if turn_id is not None and not isinstance(turn_id, str):
            raise AppServerError("turn/start returned an invalid turn id")
        return StartedTask(thread_id, turn_id, str(cwd), title, effective_model, effective_effort)

    def list_tasks(
        self,
        *,
        limit: int,
        cursor: str | None,
        cwd: Path | None,
        archived: bool,
        search_term: str | None,
        project_id: str | None,
        section_id: str | None,
        parent_thread_id: str | None,
        ancestor_thread_id: str | None,
        sort_key: str | None,
        sort_direction: str | None,
        source_kinds: list[str] | None,
        use_state_db_only: bool,
    ) -> ListedTasks:
        """List task summaries using the app-server's thread/list method."""

        if parent_thread_id and ancestor_thread_id:
            raise AppServerError("parent-thread-id and ancestor-thread-id are mutually exclusive")
        params: dict[str, Any] = {
            "limit": limit,
            "archived": archived,
            "useStateDbOnly": use_state_db_only,
        }
        optional = {
            "cursor": cursor,
            "cwd": str(cwd) if cwd is not None else None,
            "searchTerm": search_term,
            "projectId": project_id,
            "sectionId": section_id,
            "parentThreadId": parent_thread_id,
            "ancestorThreadId": ancestor_thread_id,
            "sortKey": sort_key,
            "sortDirection": sort_direction,
        }
        params.update({key: value for key, value in optional.items() if value is not None})
        if source_kinds:
            params["sourceKinds"] = source_kinds
        result = self._request("thread/list", params)
        data = result.get("data")
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise AppServerError("thread/list returned an invalid data page")
        return ListedTasks(
            data=data,
            next_cursor=result.get("nextCursor") if isinstance(result.get("nextCursor"), str) else None,
            backwards_cursor=(
                result.get("backwardsCursor")
                if isinstance(result.get("backwardsCursor"), str)
                else None
            ),
        )

    def delete_task(self, thread_id: str) -> dict[str, Any]:
        """Permanently delete a task through the app-server."""

        self._request("thread/delete", {"threadId": thread_id})
        return {"threadId": thread_id, "deleted": True}

    def rename_task(self, *, thread_id: str, title: str) -> dict[str, str]:
        """Set the user-facing name of a durable task through the app-server."""

        if not title.strip():
            raise AppServerError("title must not be empty")
        self._request("thread/name/set", {"threadId": thread_id, "name": title})
        return {"threadId": thread_id, "title": title}

    def queue_message(
        self,
        *,
        thread_id: str,
        message: str,
        model: str | None,
        effort: str | None,
    ) -> QueuedMessage:
        """Load a durable thread when necessary, then queue one message.

        ``thread/queue/add`` deliberately persists messages without loading an
        unloaded thread. This method reads the authoritative status first and
        uses ``thread/resume`` without input for a cold thread. Optional model
        and reasoning-effort settings are applied before the message is queued.
        """

        read = self._request(
            "thread/read", {"threadId": thread_id, "includeTurns": False}
        )
        thread = read.get("thread")
        if not isinstance(thread, dict):
            raise AppServerError("thread/read returned no thread")
        status = thread.get("status")
        previous_status = status.get("type") if isinstance(status, dict) else None
        if not isinstance(previous_status, str):
            raise AppServerError("thread/read returned a thread without a status")
        if previous_status == "systemError":
            raise AppServerError("thread is in systemError state and cannot be queued")

        resumed = previous_status == "notLoaded"
        effective_thread = thread
        if resumed:
            resume_params: dict[str, Any] = {
                "threadId": thread_id,
                "excludeTurns": True,
            }
            if model is not None:
                resume_params["model"] = model
            resumed_result = self._request("thread/resume", resume_params)
            resumed_thread = resumed_result.get("thread")
            if not isinstance(resumed_thread, dict):
                raise AppServerError("thread/resume returned no thread")
            effective_thread = resumed_thread

        settings_updated = (model is not None and not resumed) or effort is not None
        if settings_updated:
            settings_params: dict[str, Any] = {"threadId": thread_id}
            if model is not None and not resumed:
                settings_params["model"] = model
            if effort is not None:
                settings_params["effort"] = effort
            self._request("thread/settings/update", settings_params)
            self._wait_for_notification(
                "thread/settings/updated",
                lambda notification: isinstance(notification.get("params"), dict)
                and notification["params"].get("threadId") == thread_id,
            )

        queued = self._request(
            "thread/queue/add",
            {
                "threadId": thread_id,
                "clientUserMessageId": str(uuid.uuid4()),
                "input": [{"type": "text", "text": message}],
            },
        )
        submission = queued.get("queuedSubmission")
        if not isinstance(submission, dict) or not isinstance(submission.get("id"), str):
            raise AppServerError("thread/queue/add returned no queued submission id")

        current_model = model if model is not None else effective_thread.get("model")
        current_effort = effort if effort is not None else effective_thread.get("reasoningEffort")
        if current_model is not None and not isinstance(current_model, str):
            raise AppServerError("thread returned an invalid model")
        if current_effort is not None and not isinstance(current_effort, str):
            raise AppServerError("thread returned an invalid reasoning effort")
        return QueuedMessage(
            thread_id=thread_id,
            queued_submission_id=submission["id"],
            previous_status=previous_status,
            resumed=resumed,
            model=current_model,
            effort=current_effort,
            settings_updated=settings_updated,
        )
