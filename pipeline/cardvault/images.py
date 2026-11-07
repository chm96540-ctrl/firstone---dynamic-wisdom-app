"""Download and cache reference card images (used only at build time, never shipped)."""

from __future__ import annotations

import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from PIL import Image


def cache_path(cache_dir: Path, card_id: str, size: str) -> Path:
    safe = card_id.replace("/", "_")
    return cache_dir / size / f"{safe}.png"


def _download(session: requests.Session, url: str, dest: Path) -> bool:
    if dest.exists():
        return True
    resp = session.get(url, timeout=60)
    if resp.status_code != 200:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    tmp.write_bytes(resp.content)
    # Re-save as PNG so every cached file decodes the same way regardless of source format.
    Image.open(tmp).convert("RGB").save(dest)
    tmp.unlink()
    return True


def download_all(
    conn: sqlite3.Connection,
    cache_dir: Path,
    size: str = "small",
    workers: int = 8,
    limit: int | None = None,
) -> tuple[int, int]:
    col = "image_small" if size == "small" else "image_large"
    sql = f"SELECT id, {col} AS url FROM cards WHERE {col} IS NOT NULL ORDER BY id"
    rows = conn.execute(sql).fetchall()[:limit]
    session = requests.Session()
    session.headers["User-Agent"] = "cardvault-pipeline/0.1"
    with ThreadPoolExecutor(workers) as pool:
        ok = list(pool.map(lambda r: _download(session, r["url"], cache_path(cache_dir, r["id"], size)), rows))
    return sum(ok), len(ok) - sum(ok)


def load(cache_dir: Path, card_id: str, size: str = "small") -> Image.Image | None:
    p = cache_path(cache_dir, card_id, size)
    return Image.open(p).convert("RGB") if p.exists() else None


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
