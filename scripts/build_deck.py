"""Build PPTX from individual slide Python modules.

Each slide module in SLIDES_DIR should export a `build(slide, prs)` function.
Usage:
  python build_deck.py --slides-dir ./slides --out deck.pptx --slide-count 10
"""

import argparse, importlib, os, sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slides-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--slide-count", type=int, required=True)
    args = parser.parse_args()

    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    sys.path.insert(0, os.path.abspath(args.slides_dir))

    for i in range(1, args.slide_count + 1):
        mod_name = f"slide_{i:02d}"
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            print(f"WARNING: {mod_name}.py not found, adding blank slide")
            prs.slides.add_slide(prs.slide_layouts[6])
            continue

        slide = prs.slides.add_slide(prs.slide_layouts[6])
        if hasattr(mod, "build"):
            mod.build(slide, prs)
        else:
            print(f"WARNING: {mod_name}.py has no build(slide, prs) function")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    prs.save(args.out)
    print(f"Saved {args.slide_count} slides to {args.out}")

if __name__ == "__main__":
    main()
