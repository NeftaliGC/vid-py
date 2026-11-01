import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Iterator, Set


@contextmanager
def get_connection(db_path: Path, create: bool = False) -> Iterator[sqlite3.Connection]:
    """
    Abre una conexión, hace commit (o rollback si hay error) y SIEMPRE la cierra.
    `with sqlite3.connect(...)` por sí solo no cierra la conexión.

    Por defecto NO crea el archivo (mode=rw): si la USB se desconectó, sqlite3.connect
    normal crearía un .db vacío en la ruta del punto de montaje. Solo init_db usa create=True.
    """
    mode = "rwc" if create else "rw"
    conn = sqlite3.connect(f"{Path(db_path).resolve().as_uri()}?mode={mode}", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


VIDPY_TABLES = {"playlist", "tracks"}


def is_vidpy_db(db_path: Path) -> bool:
    """
    True si el archivo es una base de datos SQLite de vidpy (tablas `playlist` y `tracks`).

    Se abre en SOLO LECTURA (mode=ro): nunca crea ni modifica archivos ajenos
    (otra app, Thumbs.db, archivos '._*.db' de macOS...). Cualquier error al
    abrirla (no es SQLite, sin permisos, está corrupta) se trata como "no es de vidpy".
    """
    try:
        conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            tables = {
                row[0] for row in
                conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
        finally:
            conn.close()
    except (sqlite3.Error, OSError):
        return False

    return VIDPY_TABLES <= tables


def init_db(db_path: Path) -> None:
    """Crea el schema inicial si no existe."""
    with get_connection(db_path, create=True) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS playlist (
                id          TEXT NOT NULL,
                url         TEXT NOT NULL,
                title       TEXT NOT NULL,
                last_synced TEXT,
                sync_offset INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS tracks (
                id            TEXT PRIMARY KEY,
                title         TEXT NOT NULL,
                duration      INTEGER,
                downloaded_at TEXT NOT NULL
            );
        """)


def insert_playlist(db_path: Path, playlist_id: str, url: str, title: str) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO playlist (id, url, title, sync_offset) VALUES (?, ?, ?, 1)",
            (playlist_id, url, title)
        )


def get_playlist(db_path: Path) -> sqlite3.Row | None:
    with get_connection(db_path) as conn:
        return conn.execute("SELECT * FROM playlist LIMIT 1").fetchone()


def get_downloaded_count(db_path: Path) -> int:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) as total FROM tracks").fetchone()
        return row["total"] if row else 0


def get_downloaded_ids(db_path: Path) -> Set[str]:
    """IDs de las canciones ya registradas (y descargadas) en la USB."""
    with get_connection(db_path) as conn:
        return {row["id"] for row in conn.execute("SELECT id FROM tracks")}


def get_sync_offset(db_path: Path) -> int:
    """Retorna el índice (1-based) desde donde debe continuar el próximo bloque."""
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT sync_offset FROM playlist LIMIT 1").fetchone()
        return row["sync_offset"] if row else 1


def set_sync_offset(db_path: Path, offset: int) -> None:
    """Guarda el índice donde quedó el sync para poder reanudar."""
    with get_connection(db_path) as conn:
        conn.execute("UPDATE playlist SET sync_offset = ?", (offset,))


def insert_track(db_path: Path, track: Dict[str, Any]) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO tracks (id, title, duration, downloaded_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                track["id"],
                track.get("title", ""),
                track.get("duration"),
                datetime.now().isoformat(),
            )
        )


def update_last_synced(db_path: Path) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE playlist SET last_synced = ?, sync_offset = 1",
            (datetime.now().isoformat(),)
        )


def get_all_tracks(db_path: Path) -> List[sqlite3.Row]:
    with get_connection(db_path) as conn:
        return conn.execute("SELECT * FROM tracks").fetchall()