"""Minimal synchronous client for the local Codex app-server WebSocket."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from websockets.sync.client import ClientConnection, unix_connect


class AppServerError(RuntimeError):
    """The app-server rejected a request or returned an invalid response."""


@dataclass(frozen=True)
class StartedTask:
    """Identifiers and effective settings returned for a newly started task."""

    thread_id: str
    turn_id: str | None
    cwd: str
    model: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "threadId": self.thread_id,
            "turnId": self.turn_id,
            "cwd": self.cwd,
            "model": self.model,
        }


class CodexAppServer:
    """Small JSON-RPC client that performs the Codex initialization handshake."""

    def __init__(self, socket_path: Path, *, timeout: float = 30.0) -> None:
        self.socket_path = socket_path
        self.timeout = timeout
        self._next_id = 1
        self._connection: ClientConnection | None = None

    def __enter__(self) -> "CodexAppServer":
        try:
            self._connection = unix_connect(
                str(self.socket_path),
                open_timeout=self.timeout,
                close_timeout=self.timeout,
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
            if self._connection is None:
                raise AppServerError("app-server connection is not open")
            try:
                raw = self._connection.recv(timeout=self.timeout)
            except TimeoutError as exc:
                raise AppServerError(f"timed out waiting for {method} response") from exc
            if raw is None:
                raise AppServerError(f"app-server closed the connection while handling {method}")
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            try:
                message = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise AppServerError("app-server returned invalid JSON") from exc
            if message.get("id") != request_id:
                # Notifications and unrelated responses may be interleaved with a request.
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
        prompt: str,
        model: str,
        sandbox: str,
        approval_policy: str,
        thread_source: str,
        session_start_source: str,
        history_mode: str,
        runtime_workspace_roots: list[Path],
        model_provider: str | None,
        allow_provider_model_fallback: bool,
    ) -> StartedTask:
        """Create a durable thread and start its first turn."""

        thread_params: dict[str, Any] = {
            "cwd": str(cwd),
            "runtimeWorkspaceRoots": [str(path) for path in runtime_workspace_roots],
            "model": model,
            "allowProviderModelFallback": allow_provider_model_fallback,
            "sandbox": sandbox,
            "approvalPolicy": approval_policy,
            "threadSource": thread_source,
            "sessionStartSource": session_start_source,
            "historyMode": history_mode,
        }
        if model_provider is not None:
            thread_params["modelProvider"] = model_provider

        thread_result = self._request("thread/start", thread_params)
        thread = thread_result.get("thread")
        if not isinstance(thread, dict) or not isinstance(thread.get("id"), str):
            raise AppServerError("thread/start returned no thread id")
        thread_id = thread["id"]

        turn_result = self._request(
            "turn/start",
            {
                "threadId": thread_id,
                "clientUserMessageId": str(uuid.uuid4()),
                "input": [{"type": "text", "text": prompt}],
                "model": model,
                "cwd": str(cwd),
                "approvalPolicy": approval_policy,
                "runtimeWorkspaceRoots": [str(path) for path in runtime_workspace_roots],
            },
        )
        turn = turn_result.get("turn")
        turn_id = turn.get("id") if isinstance(turn, dict) else None
        if turn_id is not None and not isinstance(turn_id, str):
            raise AppServerError("turn/start returned an invalid turn id")
        return StartedTask(thread_id, turn_id, str(cwd), model)
