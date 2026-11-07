"""Client for the pokemontcg.io v2 API (https://docs.pokemontcg.io).

Works without an API key (rate-limited); set POKEMONTCG_API_KEY for higher limits.
Every response is normalised into plain dicts that match the catalog schema, so the
rest of the pipeline never touches the raw API shape.
"""

from __future__ import annotations

import os
import time
from datetime import date
from typing import Iterator

import requests

BASE_URL = "https://api.pokemontcg.io/v2"
PAGE_SIZE = 250


class PokemonTcgClient:
    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        self.session = session or requests.Session()
        key = api_key or os.environ.get("POKEMONTCG_API_KEY")
        if key:
            self.session.headers["X-Api-Key"] = key
        self.session.headers["User-Agent"] = "cardvault-pipeline/0.1"

    def _get(self, path: str, params: dict | None = None, retries: int = 5) -> dict:
        delay = 2.0
        for attempt in range(retries):
            resp = self.session.get(f"{BASE_URL}{path}", params=params, timeout=60)
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError("unreachable")

    def _paged(self, path: str, params: dict | None = None) -> Iterator[dict]:
        page = 1
        while True:
            body = self._get(path, {**(params or {}), "page": page, "pageSize": PAGE_SIZE})
            yield from body.get("data", [])
            if page * body.get("pageSize", PAGE_SIZE) >= body.get("totalCount", 0):
                return
            page += 1

    def sets(self) -> Iterator[dict]:
        for raw in self._paged("/sets", {"orderBy": "releaseDate"}):
            yield normalize_set(raw)

    def cards(self, set_id: str | None = None) -> Iterator[dict]:
        """Yields raw card payloads (normalise with normalize_card / extract_prices)."""
        params = {"q": f"set.id:{set_id}"} if set_id else {}
        yield from self._paged("/cards", params)


# ------------------------------------------------------------ normalisers


def normalize_set(raw: dict) -> dict:
    return {
        "id": raw["id"],
        "name": raw["name"],
        "series": raw.get("series"),
        "printed_total": raw.get("printedTotal"),
        "total": raw.get("total"),
        "release_date": (raw.get("releaseDate") or "").replace("/", "-") or None,
        "symbol_url": (raw.get("images") or {}).get("symbol"),
    }


def normalize_card(raw: dict) -> dict:
    images = raw.get("images") or {}
    tcg_prices = ((raw.get("tcgplayer") or {}).get("prices")) or {}
    return {
        "id": raw["id"],
        "set_id": raw["set"]["id"],
        "name": raw["name"],
        "number": raw["number"],
        "supertype": raw.get("supertype"),
        "subtypes": raw.get("subtypes") or [],
        "rarity": raw.get("rarity"),
        "artist": raw.get("artist"),
        "image_small": images.get("small"),
        "image_large": images.get("large"),
        # The print variants TCGplayer tracks are the best available list of
        # what physically exists (normal / holofoil / reverseHolofoil / 1stEdition...).
        "variants": sorted(tcg_prices.keys()),
    }


def extract_prices(raw: dict, today: date | None = None) -> list[dict]:
    """One snapshot row per (variant, currency, source) found on the card payload."""
    today_s = (today or date.today()).isoformat()
    rows: list[dict] = []

    for variant, p in (((raw.get("tcgplayer") or {}).get("prices")) or {}).items():
        if not p:
            continue
        rows.append(
            {
                "card_id": raw["id"],
                "variant": variant,
                "currency": "USD",
                "source": "tcgplayer",
                "date": today_s,
                "market": p.get("market"),
                "low": p.get("low"),
                "mid": p.get("mid"),
                "high": p.get("high"),
            }
        )

    cm = ((raw.get("cardmarket") or {}).get("prices")) or {}
    if cm.get("trendPrice") is not None or cm.get("avg30") is not None:
        rows.append(
            {
                "card_id": raw["id"],
                "variant": "normal",
                "currency": "EUR",
                "source": "cardmarket",
                "date": today_s,
                "market": cm.get("trendPrice") or cm.get("avg30"),
                "low": cm.get("lowPrice"),
                "mid": cm.get("avg30"),
                "high": None,
            }
        )
    if cm.get("reverseHoloTrend"):
        rows.append(
            {
                "card_id": raw["id"],
                "variant": "reverseHolofoil",
                "currency": "EUR",
                "source": "cardmarket",
                "date": today_s,
                "market": cm.get("reverseHoloTrend"),
                "low": cm.get("reverseHoloLow"),
                "mid": cm.get("reverseHoloAvg30"),
                "high": None,
            }
        )
    return rows
