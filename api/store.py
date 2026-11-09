"""One browser session, two SQLite databases, one undo snapshot per database.

The guided demo and Explore never share a file. That matches the Streamlit
app, which keeps st.session_state.db and explore_db apart.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path

from src.engine import build_database, connect

from api.errors import APIError

COOKIE = "harbor_session"
_ID = re.compile(r"^[a-f0-9]{32}$")
_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def sessions_root() -> Path:
    override = os.environ.get("HARBOR_API_SESSIONS", "")
    root = Path(override) if override else Path("/tmp/harbor-api-sessions")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _lock(session_id: str) -> threading.Lock:
    with _LOCKS_GUARD:
        lock = _LOCKS.get(session_id)
        if lock is None:
            lock = threading.Lock()
            _LOCKS[session_id] = lock
        return lock


def _blank_meta() -> dict:
    return {
        "step": 0,
        "explore_role": None,
        "explore_page": None,
        "explore_live_calls": 0,
        "guided_live_calls": 0,
        "undo_guided": None,
        "undo_explore": None,
        "ask_cache": {},
        "member_cache": {},
        "desk_searches": {},
        "feedback_seen": [],
    }


class Session:
    def __init__(self, session_id: str):
        self.id = session_id
        self.root = sessions_root() / session_id
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = _lock(session_id)

    def meta(self) -> dict:
        path = self.root / "meta.json"
        data = _blank_meta()
        if path.exists():
            try:
                loaded = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                loaded = {}
            if isinstance(loaded, dict):
                data.update(loaded)
        return data

    def save_meta(self, data: dict) -> None:
        path = self.root / "meta.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(data))
        temporary.replace(path)

    def db_path(self, world: str) -> Path:
        name = "guided.sqlite" if world == "guided" else "explore.sqlite"
        return self.root / name

    def ensure_guided(self) -> None:
        path = self.db_path("guided")
        if not path.exists():
            build_database(str(path), "start")
            meta = self.meta()
            meta["step"] = 0
            self.save_meta(meta)

    def ensure_explore(self) -> None:
        path = self.db_path("explore")
        if path.exists():
            return
        build_database(str(path), "explore")
        meta = self.meta()
        meta["explore_live_calls"] = 0
        meta["ask_cache"] = {}
        meta["member_cache"] = {}
        meta["desk_searches"] = {}
        meta["feedback_seen"] = []
        self.save_meta(meta)

    def explore_ready(self) -> bool:
        return self.db_path("explore").exists()

    @contextmanager
    def connection(self, world: str):
        if world == "guided":
            self.ensure_guided()
        elif not self.explore_ready():
            raise APIError("Open an Explore role before using the sandbox.")
        conn = connect(str(self.db_path(world)))
        try:
            yield conn
        finally:
            conn.close()

    def _undo_paths(self, world: str) -> dict[str, Path]:
        return {
            "db": self.root / f"undo-{world}.sqlite",
            "meta": self.root / f"undo-meta-{world}.json",
            "prev_db": self.root / f"undo-prev-{world}.sqlite",
            "prev_meta": self.root / f"undo-meta-prev-{world}.json",
        }

    def _rotate(self, source: Path, dest: Path) -> None:
        if not source.exists():
            return
        if dest.exists():
            dest.unlink()
        source.replace(dest)

    def snapshot(self, world: str, label: str, *, screen: int | None = None, restore_screen: int | None = None) -> None:
        """Copy the database and session meta before a change. One level is kept.

        The previous snapshot is held aside until the action succeeds, so a
        rejected action can put that undo back.
        """
        source_path = self.db_path(world)
        if not source_path.exists():
            raise APIError("There is no database to snapshot.")
        paths = self._undo_paths(world)
        self._rotate(paths["db"], paths["prev_db"])
        self._rotate(paths["meta"], paths["prev_meta"])
        source = sqlite3.connect(source_path)
        target = sqlite3.connect(paths["db"])
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        paths["meta"].write_text(json.dumps(self.meta()))
        meta = self.meta()
        from src.engine import _ACTOR, _RESOURCE

        meta[f"undo_{world}"] = {
            "label": label,
            "screen": screen,
            "restore_screen": restore_screen,
            "actor": _ACTOR.get() or "",
            "resource": _RESOURCE.get() or "",
        }
        self.save_meta(meta)

    def undo_info(self, world: str) -> dict | None:
        info = self.meta().get(f"undo_{world}")
        return info if isinstance(info, dict) else None

    def clear_undo(self, world: str) -> None:
        meta = self.meta()
        meta[f"undo_{world}"] = None
        self.save_meta(meta)
        for path in self._undo_paths(world).values():
            if path.exists():
                path.unlink()

    def _drop_previous(self, world: str) -> None:
        paths = self._undo_paths(world)
        for name in ("prev_db", "prev_meta"):
            if paths[name].exists():
                paths[name].unlink()

    def abort(self, world: str) -> None:
        """Roll back a failed action and keep the undo that was already available."""
        paths = self._undo_paths(world)
        if not paths["db"].exists() or not paths["meta"].exists():
            return
        current = self.db_path(world)
        if current.exists():
            current.unlink()
        paths["db"].replace(current)
        restored = json.loads(paths["meta"].read_text())
        if not isinstance(restored, dict):
            restored = _blank_meta()
        self.save_meta(restored)
        paths["meta"].unlink()
        if paths["prev_db"].exists():
            paths["prev_db"].replace(paths["db"])
        if paths["prev_meta"].exists():
            paths["prev_meta"].replace(paths["meta"])

    def restore(self, world: str) -> dict:
        info = self.undo_info(world)
        paths = self._undo_paths(world)
        if info is None or not paths["db"].exists() or not paths["meta"].exists():
            raise APIError("Nothing to undo.")
        current = self.db_path(world)
        if current.exists():
            current.unlink()
        paths["db"].replace(current)
        restored = json.loads(paths["meta"].read_text())
        if not isinstance(restored, dict):
            restored = _blank_meta()
        restored["undo_guided"] = None
        restored["undo_explore"] = None
        self.save_meta(restored)
        if paths["meta"].exists():
            paths["meta"].unlink()
        self._drop_previous(world)
        return info

    @contextmanager
    def mutation(self, world: str, label: str, *, screen: int | None = None, restore_screen: int | None = None):
        self.snapshot(world, label, screen=screen, restore_screen=restore_screen)
        try:
            with self.connection(world) as conn:
                yield conn
        except Exception:
            self.abort(world)
            raise
        else:
            self._drop_previous(world)

    def rebuild(self, world: str, mode: str, label: str, *, restore_screen: int | None = None) -> None:
        self.snapshot(world, label, screen=0, restore_screen=restore_screen)
        try:
            build_database(str(self.db_path(world)), mode)
        except Exception:
            self.abort(world)
            raise
        else:
            self._drop_previous(world)


def open_session(cookie: str | None) -> Session:
    session_id = cookie if cookie and _ID.match(cookie) else uuid.uuid4().hex
    session = Session(session_id)
    with session._lock:
        session.ensure_guided()
    return session
