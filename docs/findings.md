# Matching experiments

## 2026-11-07: first test on real card images

**Setup.** 669 real cards from four sets chosen to be hard:
Base Set (base1), Base Set 2 (base4, reprints Base Set artwork), Obsidian Flames (sv3),
151 (sv3pt5, many of the same Pokémon again). Each official image was degraded into
synthetic "phone photos" (`cardvault.augment`) and matched against all 669 references.

**Results (severity 1.0 = typical photo, 1.5 = poor photo)**

| Embedder | Severity | Top-1 | Top-5 | Top-1 + collector number |
|---|---|---|---|---|
| tiny (pixel thumbnail baseline) | 1.0 | 98.1% | 99.9% | 99.5% |
| tiny | 1.5 | 92.3% | 97.2% | 96.1% |
| MobileCLIP-S1 (off the shelf) | 1.0 | 92.1% | 99.6% | 97.8% |
| MobileCLIP-S1 | 1.5 | 84.0% | 95.9% | 93.4% |

Error breakdown at severity 1.5 (2 photos per card):

| Embedder | Exact | Right Pokémon, wrong printing | Wrong card |
|---|---|---|---|
| tiny | 92.8% | 1.6% | 5.6% |
| MobileCLIP-S1 | 83.7% | 8.4% | 7.9% |

**What this means**

* The approach is sound: the right card is in the top 5 for 96–99% of photos, using
  nothing but image matching on the device.
* Mistakes cluster in one predictable place: **vintage cards**, which share an identical
  yellow-frame layout and were reprinted with the same art (Base Set vs Base Set 2).
  The collector-number check is what separates those reprints, so on-device OCR of the number
  is a required part of the design, not optional.
* Off-the-shelf CLIP is **worse** than the pixel baseline here. CLIP is trained to
  recognise *what* is in a picture ("a Charizard"), not *which exact print* it is.
  So "use a bigger AI model" is not automatically the answer.
* Caveat: this test flatters the pixel baseline, because each "photo" is made from the same
  pixels as its reference. Real photos (holo foil shine, different printing, lighting)
  will hurt the pixel baseline much more than CLIP. **Real photos are the deciding test.**

**Next**

1. Collect 50–100 real phone photos of cards (any sets in the catalog), cropped to the card,
   named by card id, and score both embedders with `cardvault match`.
2. Try a retrieval-oriented model (DINOv2-small), which is known to be better at
   "same exact object" matching than CLIP.
3. If neither is good enough on real photos, fine-tune with `augment.py` (metric learning)
   so the model learns to tell apart printings, not just Pokémon.
