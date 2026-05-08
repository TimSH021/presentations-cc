#!/usr/bin/env python3
"""Inspect a template PPTX: extract slide metadata, media, fonts, structure.

Uses python-pptx for slide info + zipfile for internal XML/font scanning.
Does NOT render preview PNGs (use render_slides.py for that).
"""

import argparse, json, re, zipfile
from pathlib import Path


def collect_fonts(pptx_path):
    """Scan PPTX XML for typeface references."""
    fonts = set()
    with zipfile.ZipFile(pptx_path) as zf:
        for name in zf.namelist():
            if not re.match(r'ppt/(?:slides|slideMasters|slideLayouts|theme)/.*\.xml$', name):
                continue
            xml = zf.read(name).decode("utf-8", errors="replace")
            for m in re.finditer(r'typeface="([^"]+)"', xml):
                fonts.add(m.group(1))
    return sorted(fonts)


def extract_media(pptx_path, out_dir):
    """Extract media files from PPTX zip to out_dir."""
    extracted = []
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(pptx_path) as zf:
        for name in zf.namelist():
            if name.startswith("ppt/media/"):
                target = out_dir / Path(name).name
                target.write_bytes(zf.read(name))
                extracted.append({
                    "entry": name,
                    "path": str(target),
                    "bytes": target.stat().st_size,
                })
    return extracted


def inspect_slides(pptx_path):
    """Extract slide-level metadata using python-pptx."""
    from pptx import Presentation
    prs = Presentation(pptx_path)
    slides_info = []
    for i, slide in enumerate(prs.slides, 1):
        texts = []
        shapes_info = []
        for shape in slide.shapes:
            shape_data = {"name": shape.name, "type": str(shape.shape_type),
                          "left": shape.left, "top": shape.top,
                          "width": shape.width, "height": shape.height}
            if shape.has_text_frame:
                shape_data["text"] = shape.text_frame.text[:500]
                texts.append(shape.text_frame.text[:500])
            if shape.has_table:
                shape_data["table_rows"] = shape.table.rows.__len__()
            shapes_info.append(shape_data)

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


def scan_package(pptx_path):
    """Scan PPTX zip contents for structure info."""
    with zipfile.ZipFile(pptx_path) as zf:
        names = zf.namelist()
    return {
        "media_count": sum(1 for n in names if n.startswith("ppt/media/")),
        "slide_xml_count": sum(1 for n in names if re.match(r'ppt/slides/slide\d+\.xml$', n)),
        "chart_count": sum(1 for n in names if re.match(r'ppt/(?:charts|embeddings/charts)/chart\d+\.xml$', n)),
        "table_slide_count": sum(
            1 for n in names
            if re.match(r'ppt/slides/slide\d+\.xml$', n)
            and b"<a:tbl>" in zf.read(n)
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pptx", required=True)
    parser.add_argument("--out-dir", default="template-inspect")
    args = parser.parse_args()

    pptx_path = Path(args.pptx).resolve()
    if not pptx_path.is_file():
        raise FileNotFoundError(f"Missing PPTX: {pptx_path}")

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    slides_info = inspect_slides(pptx_path)
    fonts = collect_fonts(pptx_path)
    package_parts = scan_package(pptx_path)
    media_dir = out_dir / "assets" / "ppt" / "media"
    media = extract_media(pptx_path, media_dir)

    manifest = {
        "source_pptx": str(pptx_path),
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        **slides_info,
        "fonts": fonts,
        "package_parts": package_parts,
        "extracted_media": media,
    }

    manifest_path = out_dir / "template-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Template manifest written to {manifest_path}")
    print(f"  Slides: {manifest['slide_count']}")
    print(f"  Fonts: {', '.join(fonts) if fonts else 'none detected'}")
    print(f"  Media files: {len(media)}")


if __name__ == "__main__":
    main()
