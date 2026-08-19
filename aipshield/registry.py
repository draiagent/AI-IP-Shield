from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone
from .models import Fingerprint

SCHEMA = """
CREATE TABLE IF NOT EXISTS fingerprints (
    watermark_token TEXT PRIMARY KEY,
    fingerprint_id TEXT NOT NULL UNIQUE,
    asset_id TEXT NOT NULL,
    copy_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    source_sha256 TEXT NOT NULL,
    protected_sha256 TEXT NOT NULL,
    source_path TEXT,
    protected_path TEXT,
    engine TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    provenance_backend TEXT,
    provenance_ref TEXT,
    signer_key_id TEXT,
    provenance_status TEXT,
    asset_type TEXT,
    page_count INTEGER,
    render_dpi INTEGER
);
CREATE INDEX IF NOT EXISTS idx_fp_asset ON fingerprints(asset_id);
CREATE INDEX IF NOT EXISTS idx_fp_copy ON fingerprints(copy_id);
"""

_MIGRATION_COLUMNS = {
    "provenance_backend": "TEXT",
    "provenance_ref": "TEXT",
    "signer_key_id": "TEXT",
    "provenance_status": "TEXT",
    "asset_type": "TEXT",
    "page_count": "INTEGER",
    "render_dpi": "INTEGER",
}


class FingerprintRegistry:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._transaction() as con:
            con.executescript(SCHEMA)
            self._migrate(con)

    def _connect(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    @contextmanager
    def _transaction(self):
        # sqlite3.Connection's own context manager only commits/rolls back;
        # it never closes the connection. On Windows the leaked handle keeps
        # the .sqlite3 file locked, so callers (e.g. tempdir cleanup) fail
        # with PermissionError. Close explicitly here.
        con = self._connect()
        try:
            with con:
                yield con
        finally:
            con.close()

    @staticmethod
    def _migrate(con: sqlite3.Connection) -> None:
        existing = {row[1] for row in con.execute("PRAGMA table_info(fingerprints)").fetchall()}
        for name, sql_type in _MIGRATION_COLUMNS.items():
            if name not in existing:
                con.execute(f"ALTER TABLE fingerprints ADD COLUMN {name} {sql_type}")

    def add(self, fp: Fingerprint, source_sha256: str, protected_sha256: str,
            source_path: str, protected_path: str, engine: str,
            provenance_backend: str | None = None,
            provenance_ref: str | None = None,
            signer_key_id: str | None = None,
            provenance_status: str | None = None,
            asset_type: str | None = None,
            page_count: int | None = None,
            render_dpi: int | None = None) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._transaction() as con:
            con.execute(
                """INSERT INTO fingerprints
                (watermark_token, fingerprint_id, asset_id, copy_id, version,
                 source_sha256, protected_sha256, source_path, protected_path,
                 engine, created_at, provenance_backend, provenance_ref,
                 signer_key_id, provenance_status, asset_type, page_count, render_dpi)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (fp.watermark_token, fp.fingerprint_id, fp.asset_id, fp.copy_id,
                 fp.version, source_sha256, protected_sha256, source_path,
                 protected_path, engine, created_at, provenance_backend,
                 provenance_ref, signer_key_id, provenance_status, asset_type,
                 page_count, render_dpi),
            )

    def get_by_token(self, token: str):
        with self._transaction() as con:
            row = con.execute(
                "SELECT * FROM fingerprints WHERE watermark_token=? AND status='active'",
                (token.upper(),),
            ).fetchone()
        return dict(row) if row else None

    def get_by_protected_sha256(self, protected_sha256: str):
        with self._transaction() as con:
            row = con.execute(
                "SELECT * FROM fingerprints WHERE protected_sha256=? AND status='active'",
                (protected_sha256,),
            ).fetchone()
        return dict(row) if row else None

    def count(self) -> int:
        with self._transaction() as con:
            return int(con.execute("SELECT COUNT(*) FROM fingerprints").fetchone()[0])
