"""Matching accuracy test: degrade every reference image, then check we still find the card.

Reports top-1 / top-5 accuracy and the most common confusions (which card got mistaken
for which). Top-5 is the number that matters most for the app, because the user picks
from a short list; top-1 decides how often they don't have to.

Optionally applies the collector-number tiebreak: among the top-k candidates, prefer
the one whose printed number matches what OCR read. Here we simulate a perfect OCR read
with a configurable miss rate, to estimate how much the tiebreak is worth before
building it in the app.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field

import numpy as np
from PIL import Image

from .augment import phone_photo
from .embed import Embedder, top_k


@dataclass
class EvalResult:
    queries: int
    top1: float
    top5: float
    top1_with_number: float | None
    confusions: list[tuple[str, str, int]] = field(default_factory=list)

    def report(self) -> str:
        lines = [
            f"queries          {self.queries}",
            f"top-1 accuracy   {self.top1:.1%}",
            f"top-5 accuracy   {self.top5:.1%}",
        ]
        if self.top1_with_number is not None:
            lines.append(f"top-1 + number   {self.top1_with_number:.1%}   (collector-number tiebreak)")
        if self.confusions:
            lines.append("most common confusions (true -> predicted):")
            lines += [f"  {t} -> {p}  x{n}" for t, p, n in self.confusions]
        return "\n".join(lines)


def evaluate(
    embedder: Embedder,
    ref_ids: list[str],
    ref_matrix: np.ndarray,
    images: dict[str, Image.Image],
    numbers: dict[str, str] | None = None,
    views: int = 3,
    severity: float = 1.0,
    ocr_miss_rate: float = 0.2,
    seed: int = 0,
) -> EvalResult:
    rng = random.Random(seed)
    index = {cid: i for i, cid in enumerate(ref_ids)}
    truth: list[int] = []
    shots: list[Image.Image] = []
    for cid, img in images.items():
        if cid not in index:
            continue
        for _ in range(views):
            truth.append(index[cid])
            shots.append(phone_photo(img, rng, severity))

    if not shots:
        raise ValueError("no query images overlap the reference set")

    q = embedder.embed(shots)
    idx, _ = top_k(q, ref_matrix, k=5)
    truth_arr = np.array(truth)
    top1 = float((idx[:, 0] == truth_arr).mean())
    top5 = float((idx == truth_arr[:, None]).any(axis=1).mean())

    with_number = None
    if numbers:
        hits = 0
        for row, t in zip(idx, truth_arr):
            pick = row[0]
            if rng.random() >= ocr_miss_rate:
                read = numbers.get(ref_ids[t])
                for cand in row:
                    if numbers.get(ref_ids[cand]) == read:
                        pick = cand
                        break
            hits += int(pick == t)
        with_number = hits / len(truth_arr)

    conf = Counter(
        (ref_ids[t], ref_ids[p]) for t, p in zip(truth_arr, idx[:, 0]) if t != p
    ).most_common(10)
    return EvalResult(
        queries=len(truth_arr),
        top1=top1,
        top5=top5,
        top1_with_number=with_number,
        confusions=[(t, p, n) for (t, p), n in conf],
    )
