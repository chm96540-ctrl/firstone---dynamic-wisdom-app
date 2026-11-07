import json
import random
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def cards_page() -> dict:
    return json.loads((FIXTURES / "cards_page.json").read_text())


def synthetic_card(seed: int, size=(245, 342)) -> Image.Image:
    """A fake 'card': coloured frame, art box with random shapes, text bars.

    Cards share a layout (like real cards do) so the matcher has to use the details.
    """
    rng = random.Random(seed)
    w, h = size
    frame = tuple(rng.randint(120, 255) for _ in range(3))
    img = Image.new("RGB", size, frame)
    d = ImageDraw.Draw(img)
    d.rectangle((12, 40, w - 12, h // 2), fill=tuple(rng.randint(0, 255) for _ in range(3)))
    for _ in range(6):
        x0, y0 = rng.randint(12, w - 60), rng.randint(40, h // 2 - 40)
        d.ellipse((x0, y0, x0 + rng.randint(20, 60), y0 + rng.randint(20, 60)),
                  fill=tuple(rng.randint(0, 255) for _ in range(3)))
    for row in range(5):
        y = h // 2 + 20 + row * 25
        d.rectangle((20, y, 20 + rng.randint(60, w - 40), y + 8), fill=(40, 40, 40))
    return img
