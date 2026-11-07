# Card Vault (working title)

An offline, privacy-first scanner for trading-card collections. Point your phone at a card,
it identifies it on the device, adds it to your collection, and shows an estimated value.
Nothing about your collection ever leaves your phone.

> Name is a placeholder. Avoid "Pokémon" in the app name, icon and store listing: it's a
> trademark of Nintendo / The Pokémon Company. Describing compatibility in the store text
> ("works with Pokémon TCG cards") is generally treated differently from using it as the name.

## How it works

```
 phone camera ──► find & straighten card ──► fingerprint (embedding) ──► nearest match in
                                                                          ~20k known cards
                                                         │
                         OCR collector number ("125/197") ┘ breaks ties between lookalikes
                                                         │
                                         user confirms from top 3 ──► collection (SQLite)
                                                                         │
                                        prices.json.gz (one file, all cards) ──► value
```

* **No big vision-language model needed.** Matching image fingerprints is faster, smaller and
  more reliable than having a model read the card. On-device OCR (Apple Vision / Google ML Kit)
  only reads the collector number.
* **No hand-labelled training data needed.** If accuracy needs a boost, `cardvault.augment`
  turns each official card image into unlimited realistic "phone photos" for fine-tuning.
* **Private price updates.** The app downloads one signed file containing every card's price,
  so no server ever learns which cards you have.

## Repo layout

| Path | What |
|---|---|
| `pipeline/` | Python build pipeline: card data, fingerprints, accuracy test, prices |
| `app/` | Mobile app (not started yet; see `app/README.md` for the plan) |
| `.github/workflows/prices.yml` | Weekly price snapshot → 52-week averages → signed release asset |

## Pipeline quick start

```bash
cd pipeline
pip install -e ".[dev]"          # add ,ml for the CLIP embedder (torch + open_clip)
pytest -q

cardvault fetch --set sv3        # one set to start; omit --set for everything (~20k cards)
cardvault images                 # reference images (build-time only, never shipped)
cardvault embed --embedder tiny  # baseline; then try --embedder clip
cardvault eval  --embedder tiny  # top-1 / top-5 accuracy on synthetic phone photos
cardvault match my_card.jpg      # top-5 guesses for your own photo (crop it to the card first)
cardvault prices                 # build/release/prices.json.gz (+ .sig if PRICE_SIGNING_KEY set)
cardvault keygen                 # one-time: signing keypair for price files
```

Data source: [pokemontcg.io](https://pokemontcg.io) (free; set `POKEMONTCG_API_KEY` for higher
rate limits). Prices come from the TCGplayer (USD) and Cardmarket (EUR) figures it publishes.

## Prices: what "52-week average" means here

There's no free source of a year of price history, so we build our own: the weekly workflow
saves a snapshot of every card's market price. `avg_52w` is the mean of the snapshots from
the last 52 weeks, and `points_52w` says how many weeks it covers. On day one that's 1, and it
grows each week. The app should show "based on N weeks" until it reaches 52.

Estimates assume **raw, near-mint** cards. Graded cards (PSA/BGS/CGC) sell for very different prices.

## Roadmap

1. **Now:** pipeline + accuracy baseline (this commit).
2. Run `fetch`/`images`/`embed`/`eval` on real data; compare `tiny` vs `clip` embedders.
3. Card detection + perspective correction (OpenCV) and real-photo test set.
4. Mobile app MVP: scan → confirm → collection → total value.
5. Fine-tune the embedder with `augment.py` if real-photo top-1 is below ~95%.
6. Later: binder-page batch scan, condition hints, Japanese cards (TCGdex), CSV export.

## License

Code: MIT. Card names, images and related marks belong to their respective owners; this
project is not affiliated with or endorsed by Nintendo, Creatures, GAME FREAK or The Pokémon Company.
