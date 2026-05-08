#!/usr/bin/env python3
"""Inspect a template PPTX: extract slide metadata, media, fonts, and structure.

Outputs:
  - template-manifest.json: full metadata, fonts, package info, extracted media
  - template-slides.ndjson: one JSON object per slide for streaming processing
  - assets/ppt/media/: extracted media files

Usage:
  python inspect_template.py --pptx template.pptx
  python inspect_template.py --pptx template.pptx --out-dir ./inspect-output
  python inspect_template.py --pptx template.pptx --preview  # render slide thumbnails
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def collect_fonts(pptx_path: Path) -> list[str]:
    """Scan PPTX XML for typeface references across slides, masters, layouts, and theme."""
    fonts: set[str] = set()
    pattern = re.compile(r'ppt/(?:slides|slideMasters|slideLayouts|theme|notesSlides|handoutMasters)/.*\.xml$')
    typeface_re = re.compile(r'typeface="([^"]+)"')
    panose_re = re.compile(r'<a:latin typeface="([^"]+)"')
    ea_re = re.compile(r'<a:ea typeface="([^"]+)"')
    cs_re = re.compile(r'<a:cs typeface="([^"]+)"')

    with zipfile.ZipFile(pptx_path) as zf:
        for name in zf.namelist():
            if not pattern.match(name):
                continue
            try:
                xml = zf.read(name).decode("utf-8", errors="replace")
            except Exception:
                continue
            for m in typeface_re.finditer(xml):
                fonts.add(m.group(1))
            for m in panose_re.finditer(xml):
                fonts.add(m.group(1))
            for m in ea_re.finditer(xml):
                fonts.add(m.group(1))
            for m in cs_re.finditer(xml):
                fonts.add(m.group(1))

    return sorted(fonts)


def extract_media(pptx_path: Path, out_dir: Path) -> list[dict]:
    """Extract all media files from the PPTX zip."""
    extracted: list[dict] = []
    out_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(pptx_path) as zf:
        for name in zf.namelist():
            if not name.startswith("ppt/media/"):
                continue
            try:
                data = zf.read(name)
            except Exception:
                continue
            target = out_dir / Path(name).name
            target.write_bytes(data)
            extracted.append({
                "entry": name,
                "path": str(target),
                "bytes": len(data),
                "ext": Path(name).suffix.lower(),
            })

    return sorted(extracted, key=lambda x: x["entry"])


def inspect_slide_elements(slide, slide_idx: int) -> dict:
    """Extract per-element data from a single slide for NDJSON output."""
    elements = []
    for shape in slide.shapes:
        el = {
            "name": shape.name,
            "shape_type": str(shape.shape_type) if shape.shape_type else "unknown",
            "left": shape.left,
            "top": shape.top,
            "width": shape.width,
            "height": shape.height,
        }
        if shape.has_text_frame:
            el["text_preview"] = shape.text_frame.text[:200]
            runs = []
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    runs.append({
                        "text": run.text[:100],
                        "font_size": run.font.size / 12700 if run.font.size else None,
                        "bold": run.font.bold,
                        "color": str(run.font.color.rgb) if run.font.color and run.font.color.rgb else None,
                    })
            el["runs"] = runs[:20]  # cap per shape
        if shape.has_table:
            try:
                el["table_rows"] = len(shape.table.rows)
                el["table_cols"] = len(shape.table.columns)
            except Exception:
                pass
        elements.append(el)

    return {
        "slide": slide_idx,
        "layout": slide.slide_layout.name if slide.slide_layout else "unknown",
        "element_count": len(elements),
        "elements": elements,
    }


def inspect_slides(pptx_path: Path) -> dict:
    """Extract slide-level metadata using python-pptx."""
    from pptx import Presentation

    prs = Presentation(str(pptx_path))
    slides_info = []

    for i, slide in enumerate(prs.slides, 1):
        texts = []
        shapes_info = []
        for shape in slide.shapes:
            sdata = {
                "name": shape.name,
                "shape_type": str(shape.shape_type) if shape.shape_type else "unknown",
                "left": shape.left,
                "top": shape.top,
                "width": shape.width,
                "height": shape.height,
            }
            if shape.has_text_frame:
                sdata["text"] = shape.text_frame.text[:500]
                texts.append(shape.text_frame.text[:500])
            if shape.has_table:
                try:
                    sdata["table_rows"] = len(shape.table.rows)
                    sdata["table_cols"] = len(shape.table.columns)
                except Exception:
                    pass
            shapes_info.append(sdata)

        slides_info.append({
            "slide": i,
            "layout": slide.slide_layout.name if slide.slide_layout else "unknown",
            "shape_count": len(shapes_info),
            "shapes": shapes_info,
            "preview_text": " ".join(texts)[:300],
        })

    return {
        "slide_count": len(prs.slides),
        "slide_width": prs.slide_width,
        "slide_height": prs.slide_height,
        "slide_layouts": [lyt.name for lyt in prs.slide_layouts],
        "slides": slides_info,
    }


def scan_package(pptx_path: Path) -> dict:
    """Scan PPTX zip contents for structural info."""
    with zipfile.ZipFile(pptx_path) as zf:
        names = zf.namelist()

    table_slide_count = 0
    chart_slide_count = 0
    with zipfile.ZipFile(pptx_path) as zf:
        for name in names:
            if re.match(r"ppt/slides/slide\d+\.xml$", name):
                try:
                    content = zf.read(name)
                    if b"<a:tbl>" in content:
                        table_slide_count += 1
                except Exception:
                    pass
            if re.match(r"ppt/charts/chart\d+\.xml$", name):
                chart_slide_count += 1

    return {
        "media_count": sum(1 for n in names if n.startswith("ppt/media/")),
        "slide_xml_count": sum(1 for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)),
        "chart_count": chart_slide_count,
        "table_slide_count": table_slide_count,
        "total_entries": len(names),
        "has_notes": any("notesSlides" in n for n in names),
        "has_macros": any(n.endswith(".bin") for n in names),
    }


def render_slide_thumbnails(pptx_path: Path, out_dir: Path) -> list[str]:
    """Render slide thumbnails if LibreOffice is available."""
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        import subprocess
        result = subprocess.run([
            "soffice", "--headless", "--convert-to", "png",
            "--outdir", str(out_dir), str(pptx_path),
        ], capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return sorted(str(p) for p in out_dir.glob("*.png"))
    except Exception:
        pass
    return []


def write_ndjson(slides_info: dict, out_dir: Path) -> Path:
    """Write per-slide element data as newline-delimited JSON."""
    ndjson_path = out_dir / "template-slides.ndjson"
    prs = __import__("pptx").Presentation(str(Path(slides_info.get("_pptx_path", ""))))
    # Rebuild element data if needed
    return ndjson_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a template PPTX")
    parser.add_argument("--pptx", required=True, help="Path to template PPTX")
    parser.add_argument("--out-dir", default="template-inspect", help="Output directory")
    parser.add_argument("--ndjson", action="store_true", help="Also write per-element NDJSON")
    parser.add_argument("--preview", action="store_true", help="Render slide thumbnail PNGs")
    args = parser.parse_args()

    pptx_path = Path(args.pptx).resolve()
    if not pptx_path.is_file():
        print(f"ERROR: Missing PPTX: {pptx_path}", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Inspecting {pptx_path.name}...")

    # Core metadata
    slides_info = inspect_slides(pptx_path)
    slides_info["_pptx_path"] = str(pptx_path)
    fonts = collect_fonts(pptx_path)
    package_parts = scan_package(pptx_path)

    # Media extraction
    media_dir = out_dir / "assets" / "ppt" / "media"
    media = extract_media(pptx_path, media_dir)

    manifest = {
        "source_pptx": str(pptx_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "slide_count": slides_info["slide_count"],
        "slide_width": slides_info["slide_width"],
        "slide_height": slides_info["slide_height"],
        "slide_layouts": slides_info["slide_layouts"],
        "slides": slides_info["slides"],
        "fonts": fonts,
        "package_parts": package_parts,
        "extracted_media": media,
    }

    manifest_path = out_dir / "template-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Manifest → {manifest_path}")
    print(f"  Slides: {manifest['slide_count']}")
    print(f"  Layouts: {', '.join(slides_info['slide_layouts'])}")
    print(f"  Fonts: {', '.join(fonts) if fonts else 'none detected'}")
    print(f"  Media files extracted: {len(media)}")

    # NDJSON output
    if args.ndjson:
        from pptx import Presentation
        prs = Presentation(str(pptx_path))
        ndjson_path = out_dir / "template-slides.ndjson"
        with open(ndjson_path, "w", encoding="utf-8") as f:
            for i, slide in enumerate(prs.slides, 1):
                el_data = inspect_slide_elements(slide, i)
                f.write(json.dumps(el_data, ensure_ascii=False) + "\n")
        print(f"NDJSON → {ndjson_path}")

    # Thumbnail previews
    if args.preview:
        thumb_dir = out_dir / "thumbnails"
        previews = render_slide_thumbnails(pptx_path, thumb_dir)
        if previews:
            print(f"Thumbnails → {len(previews)} slides in {thumb_dir}")
        else:
            print("Thumbnails not available (install LibreOffice)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
