import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from app.settings import DB_PATH

_db_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_cursor():
    with _db_lock:
        conn = _connect()
        try:
            cur = conn.cursor()
            yield cur
            conn.commit()
        finally:
            conn.close()


def init_db() -> None:
    with db_cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS voices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                ref_wav_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS calls (
                id TEXT PRIMARY KEY,
                to_number TEXT NOT NULL,
                voice_name TEXT NOT NULL,
                initial_message TEXT,
                status TEXT DEFAULT 'in_progress',
                summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                audio_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


# Voices

def upsert_voice(name: str, ref_wav_path: str) -> None:
    with db_cursor() as cur:
        cur.execute(
            "INSERT OR REPLACE INTO voices(name, ref_wav_path) VALUES(?, ?)",
            (name, ref_wav_path),
        )


def list_voices() -> List[Dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute("SELECT name, ref_wav_path, created_at FROM voices ORDER BY created_at DESC")
        return [dict(row) for row in cur.fetchall()]


def get_voice(name: str) -> Optional[Dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute("SELECT name, ref_wav_path FROM voices WHERE name = ?", (name,))
        row = cur.fetchone()
        return dict(row) if row else None


def delete_voice(name: str) -> None:
    with db_cursor() as cur:
        cur.execute("DELETE FROM voices WHERE name = ?", (name,))


# Calls and transcripts

def create_call(call_id: str, to_number: str, voice_name: str, initial_message: str | None) -> None:
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO calls(id, to_number, voice_name, initial_message) VALUES(?, ?, ?, ?)",
            (call_id, to_number, voice_name, initial_message),
        )


def update_call_status(call_id: str, status: str) -> None:
    with db_cursor() as cur:
        cur.execute(
            "UPDATE calls SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, call_id),
        )


def complete_call_with_summary(call_id: str, summary: str) -> None:
    with db_cursor() as cur:
        cur.execute(
            "UPDATE calls SET status = 'completed', summary = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (summary, call_id),
        )


def append_transcript(call_id: str, role: str, text: str, audio_path: str | None = None) -> None:
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO transcripts(call_id, role, text, audio_path) VALUES(?, ?, ?, ?)",
            (call_id, role, text, audio_path),
        )


def get_transcript(call_id: str) -> List[Dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute(
            "SELECT role, text, audio_path, created_at FROM transcripts WHERE call_id = ? ORDER BY id ASC",
            (call_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def list_calls() -> List[Dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, to_number, voice_name, status, summary, created_at FROM calls ORDER BY created_at DESC"
        )
        return [dict(r) for r in cur.fetchall()]