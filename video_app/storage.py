import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional


def default_data_dir() -> Path:
    path = Path(os.getenv("GVA_DATA_DIR", Path.home() / ".gemini_video_assemble"))
    path.mkdir(parents=True, exist_ok=True)
    return path


class DataStore:
    """SQLite-backed storage for config and run history."""

    def __init__(self, db_path: str | Path | None = None):
        data_dir = default_data_dir()
        self.path = Path(db_path or data_dir / "data.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    prompt TEXT,
                    duration INTEGER,
                    scenes INTEGER,
                    aspect TEXT,
                    image_provider TEXT,
                    output_path TEXT,
                    status TEXT,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    # Config helpers
    def get_config(self) -> Dict[str, str]:
        with self._conn() as conn:
            rows = conn.execute("SELECT key, value FROM config").fetchall()
            return {k: v for k, v in rows}

    def set_config(self, values: Mapping[str, str]) -> Dict[str, str]:
        filtered = {k: v for k, v in values.items() if v is not None}
        with self._conn() as conn:
            for key, value in filtered.items():
                conn.execute(
                    "INSERT INTO config(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value),
                )
        return self.get_config()

    # Run helpers
    def record_run(
        self,
        prompt: str,
        duration: int,
        scenes: int,
        aspect: str,
        image_provider: str,
        status: str = "pending",
        output_path: Optional[str] = None,
        error: Optional[str] = None,
    ) -> str:
        run_id = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO runs(id, prompt, duration, scenes, aspect, image_provider, output_path, status, error)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, prompt, duration, scenes, aspect, image_provider, output_path, status, error),
            )
        return run_id

    def update_run(self, run_id: str, status: str, output_path: Optional[str] = None, error: Optional[str] = None):
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE runs SET status=?, output_path=COALESCE(?, output_path), error=?
                WHERE id=?
                """,
                (status, output_path, error, run_id),
            )

    def list_runs(self, limit: int = 25) -> List[Dict[str, str]]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, prompt, duration, scenes, aspect, image_provider, output_path, status, error, created_at
                FROM runs ORDER BY datetime(created_at) DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
            columns = [
                "id",
                "prompt",
                "duration",
                "scenes",
                "aspect",
                "image_provider",
                "output_path",
                "status",
                "error",
                "created_at",
            ]
            return [dict(zip(columns, row)) for row in rows]

    def purge(self, delete_outputs: bool = False, output_dir: Optional[Path] = None) -> None:
        if self.path.exists():
            try:
                self.path.unlink()
            except OSError:
                pass
        if delete_outputs and output_dir and output_dir.exists():
            try:
                for child in output_dir.iterdir():
                    child.unlink(missing_ok=True)
            except Exception:
                pass
        # Recreate empty db so future calls succeed
        self._init_db()
