#!/usr/bin/env python3
"""Render PPTX slides to PNG previews via LibreOffice, Ghostscript, or python-pptx fallback.

Usage:
  python render_slides.py --pptx deck.pptx --output-dir ./preview
  python render_slides.py --pptx deck.pptx --output-dir ./preview --format pdf
  python render_slides.py --pptx deck.pptx --output-dir ./preview --dpi 200
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _has_command(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def render_libreoffice(pptx_path: Path, output_dir: Path, fmt: str = "png") -> bool:
    """Convert PPTX to PNG/PDF via headless LibreOffice."""
    if not _has_command("soffice"):
        return False

    cmd = [
        "soffice", "--headless", "--convert-to", fmt,
        "--outdir", str(output_dir), str(pptx_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if stderr:
            print(f"LibreOffice warning: {stderr[:200]}", file=sys.stderr)
    return any(output_dir.glob(f"*.{fmt}"))


def render_ghostscript(pptx_path: Path, output_dir: Path, dpi: int = 150) -> bool:
    """Convert PPTX → PDF via LibreOffice, then PDF → PNG via Ghostscript."""
    if not _has_command("gs"):
        return False

    pdf_dir = output_dir / "_pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    if not render_libreoffice(pptx_path, pdf_dir, fmt="pdf"):
        return False

    pdf_path = pdf_dir / (pptx_path.stem + ".pdf")
    if not pdf_path.is_file():
        return False

    result = subprocess.run([
        "gs", "-dNOPAUSE", "-dBATCH", "-sDEVICE=png16m",
        f"-r{dpi}", f"-sOutputFile={output_dir}/slide-%02d.png",
        str(pdf_path),
    ], capture_output=True, text=True, timeout=120)

    return result.returncode == 0 and any(output_dir.glob("slide-*.png"))


def render_python_pptx_fallback(pptx_path: Path, output_dir: Path, max_slides: int = 3) -> list[str]:
    """Minimal fallback: export slide thumbnails via PIL if LibreOffice is unavailable."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        from pptx import Presentation
    except ImportError:
        return []

    prs = Presentation(str(pptx_path))
    output_dir.mkdir(parents=True, exist_ok=True)
    previews = []

    for i, slide in enumerate(prs.slides, 1):
        if i > max_slides:
            break

        # Create a simple placeholder image with slide text
        img = Image.new("RGB", (1280, 720), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Draw slide number and first text lines
        y = 40
        draw.text((40, y), f"Slide {i}", fill=(60, 60, 60))
        y += 60

        for shape in slide.shapes:
            if shape.has_text_frame and y < 680:
                text = shape.text_frame.text[:100]
                draw.text((40, y), text, fill=(100, 100, 100))
                y += 30

        out_path = output_dir / f"slide-{i:02d}.png"
        img.save(str(out_path))
        previews.append(str(out_path))

    if previews:
        print(f"PIL fallback rendered {len(previews)} placeholder slides (max {max_slides})")
    return previews


def main() -> int:
    parser = argparse.ArgumentParser(description="Render PPTX slides to PNG/PDF")
    parser.add_argument("--pptx", required=True, help="Path to PPTX file")
    parser.add_argument("--output-dir", required=True, help="Directory for rendered output")
    parser.add_argument("--format", default="png", choices=["png", "pdf"], help="Output format (default: png)")
    parser.add_argument("--dpi", type=int, default=150, help="Render DPI for PNG (default: 150)")
    parser.add_argument("--max-fallback", type=int, default=3, help="Max slides to render with PIL fallback (default: 3)")
    args = parser.parse_args()

    pptx_path = Path(args.pptx).resolve()
    if not pptx_path.is_file():
        print(f"ERROR: PPTX not found: {pptx_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.format == "pdf":
        if render_libreoffice(pptx_path, output_dir, fmt="pdf"):
            pdf_path = output_dir / (pptx_path.stem + ".pdf")
            print(f"Rendered PDF → {pdf_path}")
            return 0
        print("ERROR: PDF rendering requires LibreOffice.", file=sys.stderr)
        return 1

    # PNG rendering
    if render_libreoffice(pptx_path, output_dir, fmt="png"):
        count = len(list(output_dir.glob("*.png")))
        print(f"Rendered {count} slides via LibreOffice → {output_dir}/")
        return 0

    if render_ghostscript(pptx_path, output_dir, dpi=args.dpi):
        count = len(list(output_dir.glob("slide-*.png")))
        print(f"Rendered {count} slides via PDF→PNG → {output_dir}/")
        return 0

    # PIL fallback
    previews = render_python_pptx_fallback(pptx_path, output_dir, max_slides=args.max_fallback)
    if previews:
        print(f"Rendered placeholder previews → {output_dir}/")
        return 0

    print("WARNING: No renderer available. Install LibreOffice or Pillow for slide previews.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
