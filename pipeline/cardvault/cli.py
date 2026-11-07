"""cardvault command line.

    cardvault fetch    [--set SET_ID ...]      cards + sets + today's price snapshot
    cardvault images   [--limit N]             download reference images (build-time only)
    cardvault embed    [--embedder tiny|clip]  fingerprint every cached image into the catalog
    cardvault eval     [--embedder ...]        accuracy test on synthetic phone photos
    cardvault prices   [--out DIR]             52-week summary -> catalog + signed prices.json.gz
    cardvault keygen                           new Ed25519 keypair for signing price files
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import date
from pathlib import Path

from . import db, images, prices
from .embed import get_embedder
from .evaluate import evaluate
from .sources.pokemontcg import PokemonTcgClient, extract_prices, normalize_card


def cmd_fetch(args: argparse.Namespace) -> None:
    client = PokemonTcgClient()
    catalog = db.connect(args.catalog)
    history = db.connect_history(args.history)
    today = date.today()

    sets = [s for s in client.sets() if not args.set or s["id"] in args.set]
    for s in sets:
        db.upsert_set(catalog, s)
    n_cards = n_prices = 0
    for s in sets:
        for raw in client.cards(s["id"]):
            db.upsert_card(catalog, normalize_card(raw))
            n_prices += prices.record_snapshots(history, extract_prices(raw, today))
            n_cards += 1
        catalog.commit()
        history.commit()
        print(f"  {s['id']:<12} {s['name']}", file=sys.stderr)
    db.set_meta(catalog, "cards_fetched_at", today.isoformat())
    catalog.commit()
    print(f"fetched {len(sets)} sets, {n_cards} cards, {n_prices} price rows")


def cmd_images(args: argparse.Namespace) -> None:
    ok, failed = images.download_all(
        db.connect(args.catalog), Path(args.cache), args.size, args.workers, args.limit
    )
    print(f"images: {ok} cached, {failed} failed")


def _cached(catalog, cache: Path, size: str, limit: int | None):
    for r in catalog.execute("SELECT id FROM cards ORDER BY id").fetchall()[:limit]:
        img = images.load(cache, r["id"], size)
        if img is not None:
            yield r["id"], img


def cmd_embed(args: argparse.Namespace) -> None:
    catalog = db.connect(args.catalog)
    embedder = get_embedder(args.embedder)
    pairs = list(_cached(catalog, Path(args.cache), args.size, args.limit))
    if not pairs:
        sys.exit("no cached images - run `cardvault images` first")
    vecs = embedder.embed(img for _, img in pairs)
    n = db.store_embeddings(catalog, embedder.name, zip((cid for cid, _ in pairs), vecs))
    db.set_meta(catalog, "embedder", embedder.name)
    catalog.commit()
    print(f"embedded {n} cards with {embedder.name} (dim {vecs.shape[1]})")


def cmd_eval(args: argparse.Namespace) -> None:
    catalog = db.connect(args.catalog)
    embedder = get_embedder(args.embedder)
    ids, mat = db.load_embeddings(catalog, embedder.name)
    if not ids:
        sys.exit(f"no embeddings for {embedder.name} - run `cardvault embed` first")
    pairs = list(_cached(catalog, Path(args.cache), args.size, None))
    random.Random(args.seed).shuffle(pairs)
    sample = dict(pairs[: args.sample])
    numbers = {r["id"]: r["number"] for r in catalog.execute("SELECT id, number FROM cards")}
    res = evaluate(
        embedder, ids, mat, sample, numbers,
        views=args.views, severity=args.severity, seed=args.seed,
    )
    print(f"embedder         {embedder.name}\nreference cards  {len(ids)}")
    print(res.report())


def cmd_prices(args: argparse.Namespace) -> None:
    history = db.connect_history(args.history)
    summary = prices.summarize(history)
    catalog = db.connect(args.catalog)
    prices.write_into_catalog(catalog, summary)
    db.set_meta(catalog, "prices_as_of", date.today().isoformat())
    catalog.commit()
    info = prices.write_signed(
        prices.build_price_file(summary), Path(args.out), os.environ.get("PRICE_SIGNING_KEY")
    )
    print(
        f"prices: {len(summary)} rows, {info['bytes'] / 1e6:.2f} MB gz, "
        f"sha256 {info['sha256'][:12]}..., signed={info['signed']}"
    )


def cmd_keygen(_: argparse.Namespace) -> None:
    priv, pub = prices.generate_keypair()
    print("PRICE_SIGNING_KEY (keep secret, store as a CI secret):")
    print(priv)
    print("\nPublic key (commit this / bake it into the app):")
    print(pub)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="cardvault", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--catalog", default="build/catalog.sqlite")
    p.add_argument("--history", default="build/price_history.sqlite")
    p.add_argument("--cache", default="build/images")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch")
    f.add_argument("--set", action="append", help="only these set ids (repeatable)")
    f.set_defaults(fn=cmd_fetch)

    i = sub.add_parser("images")
    i.add_argument("--size", choices=["small", "large"], default="small")
    i.add_argument("--workers", type=int, default=8)
    i.add_argument("--limit", type=int)
    i.set_defaults(fn=cmd_images)

    e = sub.add_parser("embed")
    e.add_argument("--embedder", default="tiny")
    e.add_argument("--size", choices=["small", "large"], default="small")
    e.add_argument("--limit", type=int)
    e.set_defaults(fn=cmd_embed)

    v = sub.add_parser("eval")
    v.add_argument("--embedder", default="tiny")
    v.add_argument("--size", choices=["small", "large"], default="small")
    v.add_argument("--sample", type=int, default=500, help="cards to test")
    v.add_argument("--views", type=int, default=3, help="synthetic photos per card")
    v.add_argument("--severity", type=float, default=1.0)
    v.add_argument("--seed", type=int, default=0)
    v.set_defaults(fn=cmd_eval)

    pr = sub.add_parser("prices")
    pr.add_argument("--out", default="build/release")
    pr.set_defaults(fn=cmd_prices)

    k = sub.add_parser("keygen")
    k.set_defaults(fn=cmd_keygen)

    args = p.parse_args(argv)
    for path in (args.catalog, args.history):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    args.fn(args)


if __name__ == "__main__":
    main()
