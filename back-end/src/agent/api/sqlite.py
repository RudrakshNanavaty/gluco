"""The app's own tables in the chat SQLite file: open, commit, always close."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    """A connection that commits (or rolls back) and is closed afterwards.

    `with sqlite3.connect(...)` alone commits but leaves the connection open.
    """
    conn = sqlite3.connect(path)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def create_table(path: Path, ddl: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.execute(ddl)
