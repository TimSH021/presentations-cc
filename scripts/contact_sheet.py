#!/usr/bin/env python3
"""Build a contact-sheet PNG from slide preview images."""

from __future__ import annotations

import argparse, math
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="+")
    parser.add_argument("--output", required=True)
    parser.add_argument("--cols", type=int, default=3)
    args = parser.parse_args()

    image_paths = [Path(p).expanduser().resolve() for p in args.images]
    for p in image_paths:
        if not p.exists():
            raise FileNotFoundError(p)

    thumbs = [Image.open(p).convert("RGB") for p in image_paths]
    tile_w = max(im.width for im in thumbs)
    tile_h = max(im.height for im in thumbs)
    label_h, pad = 48, 18
    cols = max(1, args.cols)
    rows = math.ceil(len(thumbs) / cols)

    sheet = Image.new("RGB", (
        cols * tile_w + (cols + 1) * pad,
        rows * (tile_h + label_h) + (rows + 1) * pad,
    ), "white")
    draw = ImageDraw.Draw(sheet)

    for idx, im in enumerate(thumbs):
        row, col = divmod(idx, cols)
        x = pad + col * (tile_w + pad)
        y = pad + row * (tile_h + label_h + pad)
        sheet.paste(im, (x, y))
        draw.text((x + 8, y + tile_h + 14), f"Slide {idx + 1:02d}", fill=(20, 30, 50))
        im.close()

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    main()
