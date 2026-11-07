from datetime import date, timedelta

import gzip
import json

import numpy as np
import pytest

from cardvault import cli, db, prices
from cardvault.embed import TinyImageEmbedder, top_k
from cardvault.evaluate import evaluate
from cardvault.images import cache_path
from cardvault.sources import pokemontcg
from cardvault.sources.pokemontcg import extract_prices, normalize_card, normalize_set

from .conftest import synthetic_card


# ------------------------------------------------------------ source parsing


def test_normalize_card(cards_page):
    c = normalize_card(cards_page["data"][0])
    assert c["id"] == "base1-4" and c["set_id"] == "base1" and c["number"] == "4"
    assert c["variants"] == ["holofoil"]
    s = normalize_set(cards_page["data"][0]["set"])
    assert s["release_date"] == "1999-01-09" and s["printed_total"] == 102


def test_extract_prices_skips_empty_variants(cards_page):
    rows = extract_prices(cards_page["data"][1], date(2026, 11, 7))
    keys = {(r["source"], r["variant"], r["currency"]) for r in rows}
    # reverseHolofoil is null on TCGplayer and 0 on Cardmarket -> neither recorded.
    assert keys == {("tcgplayer", "normal", "USD"), ("cardmarket", "normal", "EUR")}
    assert all(r["date"] == "2026-11-07" for r in rows)


# ----------------------------------------------------------------- storage


def test_embedding_roundtrip_is_close(tmp_path):
    conn = db.connect(tmp_path / "c.sqlite")
    db.upsert_set(conn, {"id": "s", "name": "S", "series": None, "printed_total": 1,
                         "total": 1, "release_date": None, "symbol_url": None})
    rng = np.random.default_rng(0)
    vecs = {}
    for i in range(5):
        cid = f"s-{i}"
        db.upsert_card(conn, {"id": cid, "set_id": "s", "name": cid, "number": str(i),
                              "supertype": None, "subtypes": [], "rarity": None, "artist": None,
                              "image_small": None, "image_large": None, "variants": []})
        v = rng.normal(size=128).astype(np.float32)
        vecs[cid] = v / np.linalg.norm(v)
    db.store_embeddings(conn, "m", vecs.items())
    ids, mat = db.load_embeddings(conn, "m")
    for cid, row in zip(ids, mat):
        assert float(row @ vecs[cid]) > 0.99  # int8 quantisation barely moves the vector


# ------------------------------------------------------------------ prices


def test_52_week_average_window(tmp_path):
    h = db.connect_history(tmp_path / "h.sqlite")
    today = date(2026, 11, 7)
    rows = []
    for weeks_ago, price in [(0, 10.0), (10, 20.0), (51, 30.0), (60, 1000.0)]:
        rows.append({"card_id": "x-1", "variant": "normal", "currency": "USD", "source": "tcgplayer",
                     "date": (today - timedelta(weeks=weeks_ago)).isoformat(),
                     "market": price, "low": None, "mid": None, "high": None})
    prices.record_snapshots(h, rows)
    [s] = prices.summarize(h, today)
    assert s["market"] == 10.0          # latest
    assert s["avg_52w"] == 20.0         # 60-weeks-ago snapshot excluded
    assert s["points_52w"] == 3
    assert s["as_of"] == today.isoformat()


def test_price_file_signature(tmp_path):
    priv, pub = prices.generate_keypair()
    payload = prices.build_price_file([
        {"card_id": "x-1", "variant": "normal", "currency": "USD", "source": "tcgplayer",
         "market": 1.5, "avg_52w": 1.2, "points_52w": 4, "as_of": "2026-11-07"}])
    info = prices.write_signed(payload, tmp_path, priv)
    blob = (tmp_path / "prices.json.gz").read_bytes()
    sig = (tmp_path / "prices.sig").read_text().strip()
    assert info["signed"] and prices.verify(blob, sig, pub)
    assert not prices.verify(blob + b"tampered", sig, pub)
    assert json.loads(gzip.decompress(blob))["cards"]["x-1"]["USD"]["normal"] == [1.5, 1.2, 4]


# ---------------------------------------------------------------- matching


def test_top_k_orders_by_similarity():
    m = np.eye(4, dtype=np.float32)
    q = np.array([[0.1, 0.9, 0.3, 0.0]], dtype=np.float32)
    idx, sims = top_k(q, m, k=3)
    assert idx[0].tolist() == [1, 2, 0]
    assert sims[0, 0] == pytest.approx(0.9)


def test_matcher_survives_phone_photo_damage():
    emb = TinyImageEmbedder()
    refs = {f"set-{i}": synthetic_card(i) for i in range(60)}
    ids = list(refs)
    mat = emb.embed(refs.values())
    numbers = {cid: cid.split("-")[1] for cid in ids}
    res = evaluate(emb, ids, mat, refs, numbers, views=3, severity=1.0, seed=1)
    assert res.queries == 180
    assert res.top5 >= 0.9, res.report()
    assert res.top1_with_number >= res.top1


# -------------------------------------------------------------- end to end


class FakeClient:
    def __init__(self, page):
        self.page = page

    def sets(self):
        seen = {}
        for raw in self.page["data"]:
            seen[raw["set"]["id"]] = normalize_set(raw["set"])
        return iter(seen.values())

    def cards(self, set_id=None):
        return (c for c in self.page["data"] if c["set"]["id"] == set_id)


def test_cli_end_to_end(tmp_path, monkeypatch, cards_page, capsys):
    monkeypatch.setattr(cli, "PokemonTcgClient", lambda: FakeClient(cards_page))
    monkeypatch.delenv("PRICE_SIGNING_KEY", raising=False)
    base = ["--catalog", str(tmp_path / "catalog.sqlite"),
            "--history", str(tmp_path / "history.sqlite"),
            "--cache", str(tmp_path / "images")]

    cli.main(base + ["fetch"])
    # Stand in for `cardvault images` (no network in tests).
    for i, card in enumerate(cards_page["data"]):
        p = cache_path(tmp_path / "images", card["id"], "small")
        p.parent.mkdir(parents=True, exist_ok=True)
        synthetic_card(i).save(p)
    cli.main(base + ["embed"])
    cli.main(base + ["eval", "--views", "2"])
    cli.main(base + ["prices", "--out", str(tmp_path / "release")])
    photo = tmp_path / "photo.jpg"
    synthetic_card(1).save(photo)  # stands in for a photo of sv3-125
    cli.main(base + ["match", str(photo), "-k", "1"])

    out = capsys.readouterr().out
    assert "1. " in out and "Charizard ex  125/197  Obsidian Flames  [sv3-125]" in out
    assert "fetched 2 sets, 2 cards" in out
    assert "embedded 2 cards" in out
    assert "top-5 accuracy   100.0%" in out

    conn = db.connect(tmp_path / "catalog.sqlite")
    row = conn.execute(
        "SELECT market, avg_52w, points_52w FROM prices "
        "WHERE card_id='base1-4' AND currency='USD' AND variant='holofoil'").fetchone()
    assert tuple(row) == (410.5, 410.5, 1)
    assert (tmp_path / "release" / "prices.json.gz").exists()
    assert not (tmp_path / "release" / "prices.sig").exists()  # no key configured


def test_client_paginates(monkeypatch):
    calls = []

    def fake_get(self, path, params=None, retries=5):
        calls.append(params["page"])
        n = 250 if params["page"] < 3 else 10
        return {"data": [{"i": i} for i in range(n)], "pageSize": 250, "totalCount": 510}

    monkeypatch.setattr(pokemontcg.PokemonTcgClient, "_get", fake_get)
    assert len(list(pokemontcg.PokemonTcgClient().cards("x"))) == 510
    assert calls == [1, 2, 3]
