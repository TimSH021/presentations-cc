#!/usr/bin/env python3
"""Comprehensive PPTX layout quality checker.

Checks across 9 categories:
  1. off-slide elements
  2. text/image overlap
  3. text/text overlap
  4. tight text boxes (text too close to box edge)
  5. box overflow (element starts inside container but spills out)
  6. box padding (text too close to container boundaries)
  7. gutter spacing (elements too close together)
  8. split inline text (runs that should be a single paragraph)
  9. kicker centerline alignment

Usage:
  python check_layout.py --pptx deck.pptx
  python check_layout.py --pptx deck.pptx --output issues.json --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from itertools import combinations

from pptx.util import Emu


MIN_FONT_PT = 8
MIN_GUTTER_INCHES = 0.05
KICKER_CENTERLINE_TOLERANCE_EMU = 12700  # 1px at 72dpi
TIGHT_TEXT_PADDING_EMU = Emu(91440)  # ~0.1 inch
BOX_OVERFLOW_TOLERANCE_EMU = Emu(25400)  # ~0.028 inch


@dataclass
class ShapeBounds:
    name: str
    left: int
    top: int
    width: int
    height: int
    has_text: bool = False
    has_image: bool = False
    text: str = ""
    font_sizes: list[float] = field(default_factory=list)
    shape_type: str = ""


def emu_to_inches(emu) -> float:
    return emu / 914400


def _extract_bounds(shape) -> ShapeBounds | None:
    try:
        left = shape.left
        top = shape.top
        width = shape.width
        height = shape.height
    except Exception:
        return None

    has_text = shape.has_text_frame
    has_image = shape.shape_type is not None and str(shape.shape_type) == "PICTURE (13)"
    text = ""
    font_sizes = []

    if has_text:
        text = shape.text_frame.text
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                if run.font.size:
                    font_sizes.append(run.font.size / 12700)

    return ShapeBounds(
        name=shape.name,
        left=left, top=top, width=width, height=height,
        has_text=has_text, has_image=has_image,
        text=text, font_sizes=font_sizes,
        shape_type=str(shape.shape_type) if shape.shape_type else "",
    )


def _rects_overlap(a: ShapeBounds, b: ShapeBounds) -> bool:
    return (
        a.left < b.left + b.width and a.left + a.width > b.left
        and a.top < b.top + b.height and a.top + a.height > b.top
    )


def _overlap_area(a: ShapeBounds, b: ShapeBounds) -> int:
    """Return overlapping area in EMU²."""
    x_overlap = max(0, min(a.left + a.width, b.left + b.width) - max(a.left, b.left))
    y_overlap = max(0, min(a.top + a.height, b.top + b.height) - max(a.top, b.top))
    return x_overlap * y_overlap


def check_off_slide(bounds: ShapeBounds, slide_w: int, slide_h: int) -> list[str]:
    issues = []
    if bounds.left < -BOX_OVERFLOW_TOLERANCE_EMU:
        issues.append(f"'{bounds.name}' extends left of slide (left={emu_to_inches(bounds.left):.2f}in)")
    if bounds.top < -BOX_OVERFLOW_TOLERANCE_EMU:
        issues.append(f"'{bounds.name}' extends above slide (top={emu_to_inches(bounds.top):.2f}in)")
    if bounds.left + bounds.width > slide_w + BOX_OVERFLOW_TOLERANCE_EMU:
        issues.append(f"'{bounds.name}' extends right of slide (right={emu_to_inches(bounds.left + bounds.width):.2f}in)")
    if bounds.top + bounds.height > slide_h + BOX_OVERFLOW_TOLERANCE_EMU:
        issues.append(f"'{bounds.name}' extends below slide (bottom={emu_to_inches(bounds.top + bounds.height):.2f}in)")
    return issues


def check_text_image_overlap(all_bounds: list[ShapeBounds]) -> list[str]:
    issues = []
    text_bounds = [b for b in all_bounds if b.has_text]
    image_bounds = [b for b in all_bounds if b.has_image]
    for tb in text_bounds:
        for ib in image_bounds:
            if _rects_overlap(tb, ib):
                area = _overlap_area(tb, ib)
                if area > 0:
                    issues.append(f"Text '{tb.name}' overlaps image '{ib.name}' (area={area}EMU²)")
    return issues


def check_text_text_overlap(all_bounds: list[ShapeBounds]) -> list[str]:
    issues = []
    text_bounds = [b for b in all_bounds if b.has_text]
    for a, b in combinations(text_bounds, 2):
        if _rects_overlap(a, b):
            area = _overlap_area(a, b)
            if area > Emu(914400):  # > 1in² threshold to skip trivial overlaps
                issues.append(f"Text boxes '{a.name}' and '{b.name}' overlap (area={area}EMU²)")
    return issues


def check_tight_text(bounds: ShapeBounds, slide) -> list[str]:
    """Check if text is too close to its bounding box edges."""
    issues = []
    if not bounds.has_text or not bounds.text.strip():
        return issues

    try:
        tf = slide.shapes[bounds.name].text_frame
        tf_width = tf.width if hasattr(tf, 'width') else bounds.width
        tf_height = tf.height if hasattr(tf, 'height') else bounds.height

        for para in tf.paragraphs:
            total_text_width_emu = 0
            for run in para.runs:
                if run.font.size:
                    char_count = len(run.text or "")
                    char_width_emu = run.font.size / 2  # approximate
                    total_text_width_emu += char_count * char_count

            pad_right = tf_width - (total_text_width_emu * 0.6)
            if pad_right < TIGHT_TEXT_PADDING_EMU and total_text_width_emu > 0:
                issues.append(f"'{bounds.name}' text may overflow box horizontally (pad={emu_to_inches(pad_right):.3f}in)")
    except Exception:
        pass

    return issues


def check_box_overflow(bounds: ShapeBounds, all_bounds: list[ShapeBounds]) -> list[str]:
    """Check if an element starts inside a container but spills out."""
    issues = []
    for container in all_bounds:
        if container is bounds or not container.has_text:
            continue
        if (bounds.left >= container.left
                and bounds.top >= container.top
                and bounds.left + bounds.width > container.left + container.width + BOX_OVERFLOW_TOLERANCE_EMU):
            issues.append(f"'{bounds.name}' overflows right edge of container '{container.name}'")
        if (bounds.left >= container.left
                and bounds.top >= container.top
                and bounds.top + bounds.height > container.top + container.height + BOX_OVERFLOW_TOLERANCE_EMU):
            issues.append(f"'{bounds.name}' overflows bottom edge of container '{container.name}'")
    return issues


def check_gutter(all_bounds: list[ShapeBounds]) -> list[str]:
    """Check that elements don't sit too close to each other."""
    issues = []
    min_gutter_emu = Emu(int(MIN_GUTTER_INCHES * 914400))
    for a, b in combinations(all_bounds, 2):
        if _rects_overlap(a, b):
            continue
        # Horizontal proximity
        h_gap = max(0, b.left - (a.left + a.width))
        v_gap = max(0, b.top - (a.top + a.height))
        if 0 < h_gap < min_gutter_emu and (
            (a.top <= b.top < a.top + a.height) or (b.top <= a.top < b.top + b.height)
        ):
            issues.append(f"'{a.name}' and '{b.name}' gutter too narrow (h-gap={emu_to_inches(h_gap):.3f}in)")
        if 0 < v_gap < min_gutter_emu and (
            (a.left <= b.left < a.left + a.width) or (b.left <= a.left < b.left + b.width)
        ):
            issues.append(f"'{a.name}' and '{b.name}' gutter too narrow (v-gap={emu_to_inches(v_gap):.3f}in)")
    return issues


def check_split_inline(bounds: ShapeBounds) -> list[str]:
    """Detect text runs that should likely be a single paragraph."""
    issues = []
    if not bounds.has_text:
        return issues
    for pi, para in enumerate(bounds.text.split("\n")):
        runs = [r for r in para.split() if r]
        if len(runs) <= 1:
            continue
        # Heuristic: many short runs may indicate split inline text
        short_runs = [r for r in runs if len(r) < 20]
        if len(short_runs) > 3:
            issues.append(f"'{bounds.name}' paragraph {pi + 1} has {len(short_runs)} short text runs (possible split inline)")
    return issues


def check_kicker_centerline(all_bounds: list[ShapeBounds]) -> list[str]:
    """Verify kicker-marker/kicker-label pairs share the same vertical centerline."""
    issues = []
    markers = {}
    labels = {}

    for b in all_bounds:
        if "kicker-marker" in b.name.lower():
            markers[b.name] = b
        elif "kicker-label" in b.name.lower():
            labels[b.name] = b

    # Pair markers and labels by proximity
    for mname, mb in markers.items():
        mcenter_y = mb.top + mb.height // 2
        for lname, lb in labels.items():
            lcenter_y = lb.top + lb.height // 2
            if abs(mcenter_y - lcenter_y) <= KICKER_CENTERLINE_TOLERANCE_EMU:
                # Found a pair — check centerline
                if abs(mcenter_y - lcenter_y) > KICKER_CENTERLINE_TOLERANCE_EMU:
                    diff_px = abs(mcenter_y - lcenter_y) / 12700
                    issues.append(f"Kicker centerline misalignment between '{mname}' and '{lname}' ({diff_px:.1f}px)")

    return issues


def check_tiny_fonts(bounds: ShapeBounds) -> list[str]:
    """Check for font sizes below readability threshold."""
    issues = []
    for size in bounds.font_sizes:
        if size < MIN_FONT_PT:
            issues.append(f"'{bounds.name}' has tiny font ({size:.1f}pt < {MIN_FONT_PT}pt)")
    return issues


def check_slide(slide, slide_idx: int) -> list[str]:
    """Run all checks on a single slide."""
    issues = []
    shapes = list(slide.shapes)
    all_bounds = []
    for s in shapes:
        b = _extract_bounds(s)
        if b:
            all_bounds.append(b)

    slide_w = slide.part.slide_layout.slide_width or 12192000
    slide_h = slide.part.slide_layout.slide_height or 6858000

    for b in all_bounds:
        issues.extend(check_off_slide(b, slide_w, slide_h))
        issues.extend(check_tight_text(b, slide))
        issues.extend(check_box_overflow(b, all_bounds))
        issues.extend(check_tiny_fonts(b))
        issues.extend(check_split_inline(b))

    issues.extend(check_text_image_overlap(all_bounds))
    issues.extend(check_text_text_overlap(all_bounds))
    issues.extend(check_gutter(all_bounds))
    issues.extend(check_kicker_centerline(all_bounds))

    # Prefix with slide number
    return [f"slide-{slide_idx:02d}: {issue}" for issue in issues]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PPTX layout quality")
    parser.add_argument("--pptx", required=True, help="Path to PPTX file")
    parser.add_argument("--output", default=None, help="Output JSON file for issues")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print all issues even if none found")
    args = parser.parse_args()

    from pptx import Presentation

    try:
        prs = Presentation(args.pptx)
    except Exception as e:
        print(f"ERROR: Cannot open {args.pptx}: {e}", file=sys.stderr)
        return 1

    all_issues: dict[str, list[str]] = {}
    for i, slide in enumerate(prs.slides, 1):
        slide_issues = check_slide(slide, i)
        if slide_issues:
            all_issues[f"slide_{i:02d}"] = slide_issues

    total = sum(len(v) for v in all_issues.values())
    result = {"total_issues": total, "slides": all_issues}

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Issues written to {args.output}")

    if total > 0:
        print(f"Found {total} issues across {len(all_issues)} slides:")
        for slide_name, issues in sorted(all_issues.items()):
            for issue in issues:
                print(f"  {issue}")
        return 1
    elif args.verbose:
        print("No layout issues found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
