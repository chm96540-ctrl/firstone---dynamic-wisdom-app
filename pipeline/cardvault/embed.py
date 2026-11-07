"""Image -> fingerprint (embedding) backends.

`tiny` is a dependency-free baseline (downscaled colour thumbnail). It is useful for
tests and as a floor to beat, not for production.

`clip` uses an open_clip model (default: MobileCLIP-S1, small enough for phones once
exported). Install with `pip install -e "pipeline[ml]"`.

Every backend returns L2-normalised float32 vectors, so cosine similarity == dot product.
The phone app must run the *same* model, so `name` is stored next to each vector.
"""

from __future__ import annotations

from typing import Iterable, Protocol

import numpy as np
from PIL import Image

# Standard card aspect ratio (63 x 88 mm).
CARD_ASPECT = 63 / 88


class Embedder(Protocol):
    name: str

    def embed(self, images: Iterable[Image.Image]) -> np.ndarray: ...


def _l2(x: np.ndarray) -> np.ndarray:
    return x / (np.linalg.norm(x, axis=-1, keepdims=True) + 1e-12)


class TinyImageEmbedder:
    """Downscale to a small RGB grid, remove brightness/contrast, flatten."""

    def __init__(self, width: int = 12, height: int = 17):
        self.size = (width, height)
        self.name = f"tiny-{width}x{height}-v1"

    def embed_one(self, img: Image.Image) -> np.ndarray:
        arr = np.asarray(
            img.convert("RGB").resize(self.size, Image.Resampling.BOX), dtype=np.float32
        )
        arr = (arr - arr.mean(axis=(0, 1))) / (arr.std(axis=(0, 1)) + 1e-6)
        return _l2(arr.reshape(-1))

    def embed(self, images: Iterable[Image.Image]) -> np.ndarray:
        return np.stack([self.embed_one(im) for im in images]).astype(np.float32)


class ClipEmbedder:
    def __init__(
        self,
        model: str = "MobileCLIP-S1",
        pretrained: str = "datacompdr",
        device: str | None = None,
        batch_size: int = 64,
    ):
        import open_clip  # noqa: PLC0415 - optional dependency
        import torch  # noqa: PLC0415

        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model, pretrained=pretrained, device=self.device
        )
        self.model.eval()
        self.batch_size = batch_size
        self.name = f"openclip-{model}-{pretrained}"

    def embed(self, images: Iterable[Image.Image]) -> np.ndarray:
        out: list[np.ndarray] = []
        batch: list = []

        def flush() -> None:
            with self.torch.no_grad():
                x = self.torch.stack(batch).to(self.device)
                out.append(self.model.encode_image(x).float().cpu().numpy())
            batch.clear()

        for im in images:
            batch.append(self.preprocess(im.convert("RGB")))
            if len(batch) == self.batch_size:
                flush()
        if batch:
            flush()
        return _l2(np.concatenate(out)).astype(np.float32)


def get_embedder(name: str) -> Embedder:
    if name == "tiny":
        return TinyImageEmbedder()
    if name == "clip":
        return ClipEmbedder()
    if name.startswith("clip:"):
        model, _, pretrained = name[5:].partition("/")
        return ClipEmbedder(model, pretrained or "openai")
    raise ValueError(f"unknown embedder {name!r} (use 'tiny', 'clip' or 'clip:MODEL/PRETRAINED')")


def top_k(query: np.ndarray, matrix: np.ndarray, k: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """Cosine nearest neighbours. Brute force is fine: 20k x 512 is ~10M multiply-adds."""
    sims = query @ matrix.T
    k = min(k, matrix.shape[0])
    idx = np.argpartition(-sims, k - 1, axis=-1)[..., :k]
    part = np.take_along_axis(sims, idx, axis=-1)
    order = np.argsort(-part, axis=-1)
    return np.take_along_axis(idx, order, axis=-1), np.take_along_axis(part, order, axis=-1)
