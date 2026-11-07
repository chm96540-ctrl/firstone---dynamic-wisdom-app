"""SQLite schema and helpers for the card catalog.

One file (`catalog.sqlite`) holds everything the phone app needs offline:
sets, cards, image fingerprints (embeddings) and the latest price summary.
Price *history* lives in a separate file (`price_history.sqlite`) that only
the build pipeline uses, so the app download stays small.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

import numpy as np

CATALOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS sets (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    series        TEXT,
    printed_total INTEGER,
    total         INTEGER,
    release_date  TEXT,
    symbol_url    TEXT
);

CREATE TABLE IF NOT EXISTS cards (
    id            TEXT PRIMARY KEY,          -- e.g. "sv3-125"
    set_id        TEXT NOT NULL REFERENCES sets(id),
    name          TEXT NOT NULL,
    number        TEXT NOT NULL,             -- collector number as printed, e.g. "125" or "TG05"
    supertype     TEXT,
    subtypes      TEXT,                      -- JSON array
    rarity        TEXT,
    artist        TEXT,
    image_small   TEXT,
    image_large   TEXT,
    variants      TEXT                       -- JSON array of known print variants
);
CREATE INDEX IF NOT EXISTS cards_by_number ON cards(number, set_id);
CREATE INDEX IF NOT EXISTS cards_by_name ON cards(name);

CREATE TABLE IF NOT EXISTS embeddings (
    card_id  TEXT NOT NULL REFERENCES cards(id),
    model    TEXT NOT NULL,                  -- embedder name + version
    dim      INTEGER NOT NULL,
    scale    REAL NOT NULL,                  -- int8 quantisation scale
    vector   BLOB NOT NULL,                  -- int8[dim]
    PRIMARY KEY (card_id, model)
);

CREATE TABLE IF NOT EXISTS prices (
    card_id     TEXT NOT NULL REFERENCES cards(id),
    variant     TEXT NOT NULL,               -- normal, holofoil, reverseHolofoil, ...
    currency    TEXT NOT NULL,
    market      REAL,                        -- latest market price
    avg_52w     REAL,                        -- mean of weekly snapshots over the last 52 weeks
    points_52w  INTEGER NOT NULL DEFAULT 0,  -- how many weekly snapshots the average used
    source      TEXT NOT NULL,
    as_of       TEXT NOT NULL,
    PRIMARY KEY (card_id, variant, currency)
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

HISTORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    card_id   TEXT NOT NULL,
    variant   TEXT NOT NULL,
    currency  TEXT NOT NULL,
    source    TEXT NOT NULL,
    date      TEXT NOT NULL,                 -- ISO date the snapshot was taken
    market    REAL,
    low       REAL,
    mid       REAL,
    high      REAL,
    PRIMARY KEY (card_id, variant, currency, source, date)
);
"""


def connect(path: str | Path, schema: str = CATALOG_SCHEMA) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(schema)
    return conn


def connect_history(path: str | Path) -> sqlite3.Connection:
    return connect(path, HISTORY_SCHEMA)


# ---------------------------------------------------------------- cards


def upsert_set(conn: sqlite3.Connection, s: dict) -> None:
    conn.execute(
        """INSERT INTO sets (id, name, series, printed_total, total, release_date, symbol_url)
           VALUES (:id, :name, :series, :printed_total, :total, :release_date, :symbol_url)
           ON CONFLICT(id) DO UPDATE SET
             name=excluded.name, series=excluded.series, printed_total=excluded.printed_total,
             total=excluded.total, release_date=excluded.release_date, symbol_url=excluded.symbol_url""",
        s,
    )


def upsert_card(conn: sqlite3.Connection, c: dict) -> None:
    row = dict(c)
    row["subtypes"] = json.dumps(row.get("subtypes") or [])
    row["variants"] = json.dumps(row.get("variants") or [])
    conn.execute(
        """INSERT INTO cards (id, set_id, name, number, supertype, subtypes, rarity, artist,
                              image_small, image_large, variants)
           VALUES (:id, :set_id, :name, :number, :supertype, :subtypes, :rarity, :artist,
                   :image_small, :image_large, :variants)
           ON CONFLICT(id) DO UPDATE SET
             set_id=excluded.set_id, name=excluded.name, number=excluded.number,
             supertype=excluded.supertype, subtypes=excluded.subtypes, rarity=excluded.rarity,
             artist=excluded.artist, image_small=excluded.image_small,
             image_large=excluded.image_large, variants=excluded.variants""",
        row,
    )


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


# ----------------------------------------------------------- embeddings


def quantize(vec: np.ndarray) -> tuple[bytes, float]:
    """L2-normalised float vector -> (int8 bytes, scale). ~4x smaller than float32."""
    vec = np.asarray(vec, dtype=np.float32)
    scale = float(np.abs(vec).max()) / 127.0 or 1.0
    q = np.clip(np.round(vec / scale), -127, 127).astype(np.int8)
    return q.tobytes(), scale


def dequantize(blob: bytes, scale: float) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.int8).astype(np.float32) * scale


def store_embeddings(
    conn: sqlite3.Connection, model: str, items: Iterable[tuple[str, np.ndarray]]
) -> int:
    n = 0
    for card_id, vec in items:
        blob, scale = quantize(vec)
        conn.execute(
            "INSERT OR REPLACE INTO embeddings (card_id, model, dim, scale, vector) "
            "VALUES (?, ?, ?, ?, ?)",
            (card_id, model, int(vec.shape[0]), scale, blob),
        )
        n += 1
    return n


def load_embeddings(conn: sqlite3.Connection, model: str) -> tuple[list[str], np.ndarray]:
    rows = conn.execute(
        "SELECT card_id, scale, vector FROM embeddings WHERE model = ? ORDER BY card_id",
        (model,),
    ).fetchall()
    if not rows:
        return [], np.zeros((0, 0), dtype=np.float32)
    ids = [r["card_id"] for r in rows]
    mat = np.stack([dequantize(r["vector"], r["scale"]) for r in rows])
    mat /= np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12
    return ids, mat
