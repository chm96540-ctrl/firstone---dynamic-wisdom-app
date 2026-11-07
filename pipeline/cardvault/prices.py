"""Weekly price snapshots -> 52-week averages -> signed, privacy-preserving price file.

How prices stay fresh without tracking users:
  1. A scheduled job takes a weekly snapshot of every card's market price into
     price_history.sqlite (the history is carried forward between runs as a release asset).
  2. From that history we compute, per card + variant: latest market price and the mean
     of all weekly snapshots in the last 52 weeks.
  3. The result is published as ONE file for all cards (prices.json.gz) plus a detached
     Ed25519 signature. The app downloads the whole file, so nobody, including us, learns
     which cards a user owns.

Until 52 weeks of history exist, `points_52w` tells the app how many weeks the average
is built from, so it can show "based on N weeks" rather than pretending.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

WINDOW_DAYS = 364


def record_snapshots(history: sqlite3.Connection, rows: list[dict]) -> int:
    history.executemany(
        """INSERT OR REPLACE INTO snapshots
           (card_id, variant, currency, source, date, market, low, mid, high)
           VALUES (:card_id, :variant, :currency, :source, :date, :market, :low, :mid, :high)""",
        rows,
    )
    return len(rows)


def summarize(history: sqlite3.Connection, as_of: date | None = None) -> list[dict]:
    """Latest market price and trailing 52-week mean per (card, variant, currency, source)."""
    as_of = as_of or date.today()
    start = (as_of - timedelta(days=WINDOW_DAYS)).isoformat()
    rows = history.execute(
        """
        WITH windowed AS (
            SELECT * FROM snapshots
            WHERE date > ? AND date <= ? AND market IS NOT NULL
        ),
        latest AS (
            SELECT card_id, variant, currency, source, MAX(date) AS d
            FROM windowed GROUP BY card_id, variant, currency, source
        )
        SELECT w.card_id, w.variant, w.currency, w.source,
               (SELECT market FROM windowed x
                 WHERE x.card_id = w.card_id AND x.variant = w.variant
                   AND x.currency = w.currency AND x.source = w.source AND x.date = l.d) AS market,
               AVG(w.market) AS avg_52w,
               COUNT(*) AS points_52w,
               l.d AS as_of
        FROM windowed w
        JOIN latest l USING (card_id, variant, currency, source)
        GROUP BY w.card_id, w.variant, w.currency, w.source
        ORDER BY w.card_id, w.variant
        """,
        (start, as_of.isoformat()),
    ).fetchall()
    return [
        {
            "card_id": r[0],
            "variant": r[1],
            "currency": r[2],
            "source": r[3],
            "market": round(r[4], 2) if r[4] is not None else None,
            "avg_52w": round(r[5], 2) if r[5] is not None else None,
            "points_52w": r[6],
            "as_of": r[7],
        }
        for r in rows
    ]


def write_into_catalog(catalog: sqlite3.Connection, summary: list[dict]) -> None:
    catalog.execute("DELETE FROM prices")
    # TCGplayer rows are USD and Cardmarket rows EUR, so the (card, variant, currency) key never collides.
    catalog.executemany(
        """INSERT OR REPLACE INTO prices
           (card_id, variant, currency, market, avg_52w, points_52w, source, as_of)
           VALUES (:card_id, :variant, :currency, :market, :avg_52w, :points_52w, :source, :as_of)""",
        summary,
    )


def build_price_file(summary: list[dict]) -> dict:
    """Compact JSON: {card_id: {"USD": {variant: [market, avg_52w, points]}}}."""
    cards: dict[str, dict] = {}
    for s in summary:
        cards.setdefault(s["card_id"], {}).setdefault(s["currency"], {})[s["variant"]] = [
            s["market"],
            s["avg_52w"],
            s["points_52w"],
        ]
    return {
        "format": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "window_days": WINDOW_DAYS,
        "fields": ["market", "avg_52w", "points_52w"],
        "cards": cards,
    }


def write_signed(payload: dict, out_dir: Path, private_key_b64: str | None = None) -> dict:
    """Write prices.json.gz + prices.sha256 (+ prices.sig if a key is supplied)."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: PLC0415

    out_dir.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    # mtime=0 keeps the gzip bytes reproducible for identical content.
    blob = gzip.compress(raw, compresslevel=9, mtime=0)
    (out_dir / "prices.json.gz").write_bytes(blob)
    digest = hashlib.sha256(blob).hexdigest()
    (out_dir / "prices.sha256").write_text(digest + "\n")
    result = {"bytes": len(blob), "sha256": digest, "signed": False}
    if private_key_b64:
        key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key_b64))
        (out_dir / "prices.sig").write_text(base64.b64encode(key.sign(blob)).decode() + "\n")
        result["signed"] = True
    return result


def verify(blob: bytes, signature_b64: str, public_key_b64: str) -> bool:
    from cryptography.exceptions import InvalidSignature  # noqa: PLC0415
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey  # noqa: PLC0415

    pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
    try:
        pub.verify(base64.b64decode(signature_b64), blob)
        return True
    except InvalidSignature:
        return False


def generate_keypair() -> tuple[str, str]:
    """(private_b64, public_b64). Private goes in a CI secret; public is baked into the app."""
    from cryptography.hazmat.primitives import serialization  # noqa: PLC0415
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: PLC0415

    key = Ed25519PrivateKey.generate()
    priv = key.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    )
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(priv).decode(), base64.b64encode(pub).decode()
