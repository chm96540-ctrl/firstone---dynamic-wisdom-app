# Mobile app (planned)

Not started yet. We start the app once `cardvault eval` on real card images gives
good numbers, so we know which embedder the phone has to run.

## Plan

* **Framework:** Expo (React Native) or Flutter, one codebase for iOS + Android.
* **Bundled data:** `catalog.sqlite` from the pipeline (cards + int8 fingerprints + baseline prices).
  Roughly 10–20 MB for ~20k cards with a 512-dim embedder. No card images are bundled.
* **Scan flow**
  1. Camera frame → detect card quadrilateral → perspective-warp to 63:88.
  2. Run the same embedder as the pipeline (exported to Core ML / TFLite / ONNX); the model
     name is stored in `meta.embedder` and must match.
  3. Cosine top-5 against the bundled fingerprints (brute force is fast enough).
  4. On-device OCR of the bottom strip (Apple Vision / ML Kit) → collector number;
     re-rank candidates whose `cards.number` matches.
  5. User confirms the card and picks a variant (normal / holo / reverse holo / 1st Edition).
* **Collection:** local SQLite table `(card_id, variant, condition, quantity, added_at)`.
  Export/import as CSV. No account, no sync by default.
* **Prices:** on user request (or weekly), download `prices.json.gz` + `prices.sig` from
  the `data-latest` GitHub release, verify the Ed25519 signature against the public key
  baked into the app, then replace the local price table. It's a whole-file download, so
  the server never sees which cards the user owns.
