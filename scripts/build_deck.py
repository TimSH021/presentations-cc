#!/usr/bin/env python3
"""Build PPTX from individual slide Python modules with preview rendering.

Each slide module in SLIDES_DIR exports a `build(slide, prs)` function.
Discovers modules via glob, builds PPTX, renders previews, generates manifest.

Usage:
  python build_deck.py --slides-dir ./slides --out deck.pptx --slide-count 10
  python build_deck.py --slides-dir ./slides --out deck.pptx --preview-dir ./previews
  python build_deck.py --slides-dir ./slides --out deck.pptx --manifest deck-manifest.json
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build PPTX from slide modules")
    parser.add_argument("--slides-dir", required=True, help="Directory containing slide_NN.py modules")
    parser.add_argument("--out", required=True, help="Output PPTX path")
    parser.add_argument("--slide-count", type=int, default=None, help="Number of slides (auto-detected if omitted)")
    parser.add_argument("--preview-dir", default=None, help="Render slide PNGs to this directory")
    parser.add_argument("--manifest", default=None, help="Write a JSON manifest of the build")
    parser.add_argument("--contact-sheet", default=None, help="Write a contact sheet grid image")
    parser.add_argument("--prs", default=None, help="Path to a .pptx template to use as base")
    return parser.parse_args()


def discover_slide_modules(slides_dir: Path) -> list[str]:
    """Find slide_NN.py files in slides_dir, return sorted module names."""
    modules = []
    for f in sorted(slides_dir.glob("slide_*.py")):
        stem = f.stem
        if stem.startswith("slide_") and stem[6:].isdigit():
            modules.append(stem)
    return modules


def build_pptx(slides_dir: Path, out_path: Path, slide_count: int | None, template_path: Path | None) -> dict:
    """Build the PPTX and return build metadata."""
    from pptx import Presentation
    from pptx.util import Inches

    if template_path and template_path.is_file():
        prs = Presentation(str(template_path))
    else:
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

    sys.path.insert(0, str(slides_dir.resolve()))

    modules = discover_slide_modules(slides_dir)
    if slide_count is None:
        slide_count = max(1, len(modules))

    built = []
    skipped = []
    empty_slide_layout = prs.slide_layouts[6]  # blank layout

    for i in range(1, slide_count + 1):
        mod_name = f"slide_{i:02d}"
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            skipped.append({"slide": i, "reason": f"{mod_name}.py not found"})
            prs.slides.add_slide(empty_slide_layout)
            continue

        slide = prs.slides.add_slide(empty_slide_layout)
        if hasattr(mod, "build"):
            try:
                mod.build(slide, prs)
                built.append(i)
            except Exception as exc:
                skipped.append({"slide": i, "reason": f"build() raised {type(exc).__name__}: {exc}"})
        else:
            skipped.append({"slide": i, "reason": f"{mod_name}.py has no build(slide, prs) function"})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))

    return {
        "total": slide_count,
        "built": len(built),
        "skipped": skipped,
        "modules_found": len(modules),
        "output": str(out_path.resolve()),
    }


def render_previews(pptx_path: Path, preview_dir: Path) -> list[str]:
    """Render slide PNGs via LibreOffice or Ghostscript fallback."""
    preview_dir.mkdir(parents=True, exist_ok=True)

    # Try LibreOffice first
    cmd = [
        "soffice", "--headless", "--convert-to", "png",
        "--outdir", str(preview_dir), str(pptx_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return sorted(str(p) for p in preview_dir.glob("*.png"))

    # Ghostscript fallback: PPTX → PDF → PNG
    try:
        subprocess.run(["gs", "--version"], capture_output=True, check=True)
        pdf_dir = preview_dir / "_pdf"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            "soffice", "--headless", "--convert-to", "pdf",
            "--outdir", str(pdf_dir), str(pptx_path),
        ], capture_output=True, check=True)
        pdf_path = pdf_dir / (pptx_path.stem + ".pdf")
        if pdf_path.is_file():
            subprocess.run([
                "gs", "-dNOPAUSE", "-dBATCH", "-sDEVICE=png16m",
                "-r150", f"-sOutputFile={preview_dir}/slide-%02d.png",
                str(pdf_path),
            ], capture_output=True, check=True)
            return sorted(str(p) for p in preview_dir.glob("slide-*.png"))
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    print("WARNING: No renderer available. Install LibreOffice for slide previews.", file=sys.stderr)
    return []


def write_manifest(meta: dict, previews: list[str], manifest_path: Path) -> Path:
    """Write a build manifest JSON file."""
    import datetime
    manifest = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        **meta,
        "previews": previews,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_path


def build_contact_sheet(preview_paths: list[str], output_path: Path, cols: int = 4) -> Path | None:
    """Combine preview PNGs into a single contact sheet grid."""
    try:
        from PIL import Image
    except ImportError:
        print("WARNING: Pillow not available for contact sheet. Install: pip install Pillow", file=sys.stderr)
        return None

    if not preview_paths:
        return None

    images = [Image.open(p) for p in preview_paths if Path(p).is_file()]
    if not images:
        return None

    thumb_w, thumb_h = images[0].size
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (thumb_w * cols, thumb_h * rows), color=(255, 255, 255))

    for idx, img in enumerate(images):
        r, c = divmod(idx, cols)
        sheet.paste(img, (c * thumb_w, r * thumb_h))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(output_path), quality=85)
    return output_path


def main() -> int:
    args = parse_args()

    slides_dir = Path(args.slides_dir).resolve()
    if not slides_dir.is_dir():
        print(f"ERROR: slides-dir not found: {slides_dir}", file=sys.stderr)
        return 1

    out_path = Path(args.out).resolve()
    template_path = Path(args.prs).resolve() if args.prs else None

    meta = build_pptx(slides_dir, out_path, args.slide_count, template_path)
    print(f"Built {meta['built']}/{meta['total']} slides → {out_path}")

    if meta["skipped"]:
        for s in meta["skipped"]:
            print(f"  SKIP slide {s['slide']}: {s['reason']}")

    previews = []
    if args.preview_dir:
        preview_dir = Path(args.preview_dir).resolve()
        previews = render_previews(out_path, preview_dir)
        if previews:
            print(f"Rendered {len(previews)} previews → {preview_dir}")
        else:
            print("Previews not available (install LibreOffice)")

    if args.contact_sheet and previews:
        contact_path = Path(args.contact_sheet).resolve()
        result = build_contact_sheet(previews, contact_path)
        if result:
            print(f"Contact sheet → {result}")

    if args.manifest:
        manifest_path = Path(args.manifest).resolve()
        result = write_manifest(meta, previews, manifest_path)
        print(f"Manifest → {result}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
