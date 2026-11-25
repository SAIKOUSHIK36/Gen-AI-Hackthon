"""SQLite persistence layer for CivicPulse AI: sessions, AI reports, chat history, and audit logs."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "civicpulse.db"


class CivicPulseDB:
    """Thread-safe SQLite storage helper for CivicPulse AI."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS upload_sessions (
                    session_id TEXT PRIMARY KEY,
                    source_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    total_rows INTEGER NOT NULL,
                    dropped_pii_columns TEXT NOT NULL,
                    inline_pii_scrubbed INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS report_history (
                    report_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    engine_mode TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    analytics_snapshot_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    message TEXT NOT NULL,
                    engine_mode TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def log_event(
        self,
        event_type: str,
        summary: str,
        session_id: str | None = None,
        actor: str = "System",
        details: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (session_id, event_type, actor, summary, details_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    event_type,
                    actor,
                    summary,
                    json.dumps(details or {}, default=str),
                    self._utc_now(),
                ),
            )

    def record_upload_session(
        self,
        session_id: str,
        source_name: str,
        file_type: str,
        total_rows: int,
        dropped_pii_columns: list[str],
        inline_pii_scrubbed: int,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO upload_sessions
                (session_id, source_name, file_type, total_rows, dropped_pii_columns, inline_pii_scrubbed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    source_name,
                    file_type,
                    int(total_rows),
                    json.dumps(dropped_pii_columns),
                    int(inline_pii_scrubbed),
                    self._utc_now(),
                ),
            )
        self.log_event(
            event_type="DATASET_INGESTED",
            session_id=session_id,
            actor="Privacy Shield",
            summary=f"Ingested {total_rows} anonymized rows from '{source_name}' ({file_type}).",
            details={
                "dropped_pii_columns": dropped_pii_columns,
                "inline_pii_scrubbed": inline_pii_scrubbed,
            },
        )

    def save_report(
        self,
        report_id: str,
        session_id: str,
        source_name: str,
        title: str,
        engine_mode: str,
        model_name: str,
        report_data: dict[str, Any],
        analytics_snapshot: dict[str, Any],
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO report_history
                (report_id, session_id, source_name, title, engine_mode, model_name, report_json, analytics_snapshot_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    session_id,
                    source_name,
                    title,
                    engine_mode,
                    model_name,
                    json.dumps(report_data, default=str),
                    json.dumps(analytics_snapshot, default=str),
                    self._utc_now(),
                ),
            )
        self.log_event(
            event_type="REPORT_GENERATED",
            session_id=session_id,
            actor=f"Gemini Engine ({model_name})",
            summary=f"Saved administrative report '{title}' ({engine_mode}).",
            details={"report_id": report_id, "engine_mode": engine_mode},
        )

    def list_reports(self, limit: int = 30) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT report_id, session_id, source_name, title, engine_mode, model_name, report_json, analytics_snapshot_json, created_at
                FROM report_history
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "report_id": r["report_id"],
                    "session_id": r["session_id"],
                    "source_name": r["source_name"],
                    "title": r["title"],
                    "engine_mode": r["engine_mode"],
                    "model_name": r["model_name"],
                    "report_data": json.loads(r["report_json"]),
                    "analytics_snapshot": json.loads(r["analytics_snapshot_json"]),
                    "created_at": r["created_at"],
                }
            )
        return out

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            r = conn.execute(
                """
                SELECT report_id, session_id, source_name, title, engine_mode, model_name, report_json, analytics_snapshot_json, created_at
                FROM report_history
                WHERE report_id = ?
                """,
                (report_id,),
            ).fetchone()
        if not r:
            return None
        return {
            "report_id": r["report_id"],
            "session_id": r["session_id"],
            "source_name": r["source_name"],
            "title": r["title"],
            "engine_mode": r["engine_mode"],
            "model_name": r["model_name"],
            "report_data": json.loads(r["report_json"]),
            "analytics_snapshot": json.loads(r["analytics_snapshot_json"]),
            "created_at": r["created_at"],
        }

    def append_chat_turn(self, session_id: str, question: str, answer: str, engine_mode: str) -> None:
        now = self._utc_now()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO chat_history (session_id, role, message, engine_mode, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, "user", question, engine_mode, now),
            )
            conn.execute(
                "INSERT INTO chat_history (session_id, role, message, engine_mode, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, "assistant", answer, engine_mode, now),
            )
        self.log_event(
            event_type="AI_QA_QUERY",
            session_id=session_id,
            actor="Ask CivicPulse AI",
            summary=f"Answered admin query: '{question[:90]}'",
            details={"engine_mode": engine_mode},
        )

    def list_chat_history(self, session_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, role, message, engine_mode, created_at
                FROM chat_history
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_audit_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, event_type, actor, summary, details_json, created_at
                FROM audit_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for r in rows:
            item = dict(r)
            item["details"] = json.loads(item.pop("details_json", "{}"))
            result.append(item)
        return result

