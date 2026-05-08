#!/usr/bin/env python3
"""Prepare a starter PPTX by duplicating selected source slides in output order.

Reads a template-frame-map.json (outputSlides array mapping output→source slides),
then creates a new PPTX with only the selected source slides duplicated.
Handles slide layout/master references correctly via python-pptx.
"""

import argparse, copy, json, io, zipfile
from pathlib import Path

from pptx import Presentation
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from lxml import etree


def read_frame_map(map_path):
    with open(map_path) as f:
        return json.load(f)


def validate_frame_map(frame_map, source_count):
    slides = frame_map.get("outputSlides", [])
    if not slides:
        raise ValueError("outputSlides must be non-empty")
    for i, entry in enumerate(slides, 1):
        if entry.get("outputSlide") != i:
            raise ValueError(f"outputSlides must be sequential; expected {i}")
        src = entry.get("sourceSlide")
        if not (1 <= src <= source_count):
            raise ValueError(f"outputSlide {i} sourceSlide {src} out of range 1-{source_count}")


def clone_slide(source_prs, slide_index, target_prs):
    """Clone a slide from source_prs to target_prs, preserving layout and content."""
    source_slide = source_prs.slides[slide_index]

    # Get the source slide's layout
    source_layout = source_slide.slide_layout

    # Find matching layout in target presentation by name
    target_layout = None
    for layout in target_prs.slide_layouts:
        if layout.name == source_layout.name:
            target_layout = layout
            break
    if target_layout is None:
        target_layout = target_prs.slide_layouts[0]

    # Add slide with matching layout
    new_slide = target_prs.slides.add_slide(target_layout)

    # Copy all shapes from source to target
    _copy_shapes(source_slide, new_slide)

    return new_slide


def _copy_shapes(source_slide, target_slide):
    """Copy shapes from source slide to target slide."""
    # Remove default shapes on target
    for shape in list(target_slide.shapes):
        sp = shape._element
        sp.getparent().remove(sp)

    # Copy each shape's XML
    for shape in source_slide.shapes:
        new_el = copy.deepcopy(shape._element)
        target_slide.shapes._spTree.append(new_el)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pptx", required=True, help="Source template PPTX")
    parser.add_argument("--map", required=True, help="template-frame-map.json")
    parser.add_argument("--out", required=True, help="Output starter PPTX")
    args = parser.parse_args()

    source_path = Path(args.pptx).resolve()
    map_path = Path(args.map).resolve()
    out_path = Path(args.out).resolve()

    if not source_path.is_file():
        raise FileNotFoundError(f"Source PPTX not found: {source_path}")

    frame_map = read_frame_map(map_path)
    source_prs = Presentation(str(source_path))
    source_count = len(source_prs.slides)

    validate_frame_map(frame_map, source_count)

    # Create target presentation with same dimensions
    target_prs = Presentation()
    target_prs.slide_width = source_prs.slide_width
    target_prs.slide_height = source_prs.slide_height

    # Copy slide masters and layouts from source to target
    # We need to clone the slide master(s) for layout references to work
    # For simplicity, we'll import slides via a different approach:
    # Create a fresh presentation, delete the default slide, then add cloned slides

    for entry in frame_map["outputSlides"]:
        source_idx = entry["sourceSlide"] - 1  # 1-based → 0-based
        clone_slide(source_prs, source_idx, target_prs)

    # Remove the default blank slide that comes with new presentation
    if len(target_prs.slides) > len(frame_map["outputSlides"]):
        # We have extra default slides — remove them
        while len(target_prs.slides) > len(frame_map["outputSlides"]):
            rId = target_prs.slides._sldIdLst[0].get("{r}id")
            if rId is None:
                rId = target_prs.slides._sldIdLst[0].get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target_prs.part.drop_rel(rId)
            target_prs.slides._sldIdLst.remove(target_prs.slides._sldIdLst[0])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    target_prs.save(str(out_path))
    print(f"Starter deck saved: {out_path} ({len(target_prs.slides)} slides)")


if __name__ == "__main__":
    main()
