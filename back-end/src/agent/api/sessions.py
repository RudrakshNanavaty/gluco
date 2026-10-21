"""Conversation memory bound to the signed-in user.

The SDK's SQLite session stores the turns under `<user_id>:<session_id>`, so one
user can never continue or read another's thread. A small index table in the
same file lists each user's threads for the UI, and a stored thread comes back
as the events it streamed, tool results and charts included.
"""

import ast
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from agents import Session, SQLiteSession
from pydantic import BaseModel, Field

from agent.api.sqlite import connect, create_table
from agent.api.sse import chart, tool_end, tool_start
from agent.domain.events import SseEvent

TITLE_LENGTH = 80


class ChatThread(BaseModel):
    """One entry in a user's thread list: the session id, a title taken from the first
    message, and when it was created and last used.
    """

    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class TranscriptMessage(BaseModel):
    """One message of a stored thread, in the same shape the stream sends.

    A user message has `text`. An assistant message has `events`: the Contract
    B events (`token`, `tool_start`, `tool_end`, `data`) it would have streamed,
    in order, so the UI rebuilds it with the reducer it uses live.
    """

    role: Literal["user", "assistant"]
    text: str = ""
    events: list[dict[str, Any]] = Field(default_factory=list)


def _text(content: Any) -> str:
    """The plain text of a message item's content (a string or content parts)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return ""


def _output(raw: Any) -> Any:
    """A tool's result as the SDK stored it: JSON, or the repr of a dict."""
    if not isinstance(raw, str):
        return raw
    for parse in (json.loads, ast.literal_eval):
        try:
            return parse(raw)
        except (ValueError, SyntaxError):
            continue
    return raw


def transcript(items: list[Any]) -> list[TranscriptMessage]:
    """Session items as messages; each turn's tool results stay in that turn."""
    messages: list[TranscriptMessage] = []
    tools: dict[str, str] = {}  # call_id -> tool name

    def assistant() -> list[dict[str, Any]]:
        if not messages or messages[-1].role != "assistant":
            messages.append(TranscriptMessage(role="assistant"))
        return messages[-1].events

    def emit(*events: SseEvent) -> None:
        assistant().extend({"type": e.name, **e.data} for e in events)

    for item in items:
        if not isinstance(item, dict):
            continue
        kind = item.get("type", "message")
        if kind == "message" and item.get("role") == "user":
            messages.append(TranscriptMessage(role="user", text=_text(item["content"])))
        elif kind == "message" and item.get("role") == "assistant":
            if text := _text(item.get("content")):
                emit(SseEvent("token", {"text": text}))
        elif kind == "function_call":
            call_id, tool = item.get("call_id", ""), item.get("name", "unknown")
            tools[call_id] = tool
            emit(tool_start(call_id, tool, item.get("arguments")))
        elif kind == "function_call_output":
            call_id = item.get("call_id", "")
            tool = tools.get(call_id, "unknown")
            output = _output(item.get("output"))
            emit(tool_end(call_id, tool, output), *chart(call_id, tool, output))
    return [m for m in messages if m.role == "user" or m.events]


class ChatSessions:
    """A user's chat threads: SQLite conversation memory keyed by user and session id,
    plus an index table for listing them.
    """

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        create_table(
            db_path,
            "CREATE TABLE IF NOT EXISTS chat_index ("
            "user_id TEXT NOT NULL, session_id TEXT NOT NULL, title TEXT NOT NULL, "
            "created_at TEXT NOT NULL, updated_at TEXT NOT NULL, "
            "PRIMARY KEY (user_id, session_id))",
        )

    @staticmethod
    def key(user_id: str, session_id: str) -> str:
        return f"{user_id}:{session_id}"

    def open(self, user_id: str, session_id: str) -> Session:
        return SQLiteSession(self.key(user_id, session_id), self._path)

    def touch(self, user_id: str, session_id: str, message: str) -> None:
        """Record activity; the first message becomes the thread's title."""
        now = datetime.now(UTC).isoformat()
        with connect(self._path) as conn:
            conn.execute(
                "INSERT INTO chat_index VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (user_id, session_id) DO UPDATE SET updated_at = ?",
                (user_id, session_id, message[:TITLE_LENGTH], now, now, now),
            )

    def threads(self, user_id: str) -> list[ChatThread]:
        with connect(self._path) as conn:
            rows = conn.execute(
                "SELECT session_id, title, created_at, updated_at FROM chat_index "
                "WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            ).fetchall()
        return [
            ChatThread(session_id=r[0], title=r[1], created_at=r[2], updated_at=r[3])
            for r in rows
        ]

    def owns(self, user_id: str, session_id: str) -> bool:
        with connect(self._path) as conn:
            row = conn.execute(
                "SELECT 1 FROM chat_index WHERE user_id = ? AND session_id = ?",
                (user_id, session_id),
            ).fetchone()
        return row is not None

    async def transcript(
        self, user_id: str, session_id: str
    ) -> list[TranscriptMessage]:
        items = await self.open(user_id, session_id).get_items()
        return transcript(list(items))
