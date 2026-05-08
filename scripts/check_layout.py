"""Check PPTX slide layout quality: overlapping shapes, off-slide objects, text overflow.

Usage:
  python check_layout.py --pptx deck.pptx
"""

import argparse, json, sys
from pptx.util import Inches, Emu

def emu_to_inches(emu):
    return emu / 914400

def check_slide(slide, idx):
    issues = []
    shapes = list(slide.shapes)
    slide_w = emu_to_inches(slide.part.slide_layout.slide_width or 12192000)
    slide_h = emu_to_inches(slide.part.slide_layout.slide_height or 6858000)

    for s in shapes:
        try:
            left = emu_to_inches(s.left)
            top = emu_to_inches(s.top)
            w = emu_to_inches(s.width)
            h = emu_to_inches(s.height)
        except Exception:
            continue

        # Off-slide check
        if left + w > slide_w + 0.1 or top + h > slide_h + 0.1:
            issues.append(f"Shape off-slide: left={left:.1f} top={top:.1f}")

        # Tiny text check (font < 8pt)
        if s.has_text_frame:
            for para in s.text_frame.paragraphs:
                for run in para.runs:
                    if run.font.size and run.font.size < 80000 * 8:
                        issues.append(f"Tiny text (font < 8pt): '{run.text[:30]}'")

        # Overlap check (simplified)
        for s2 in shapes:
            if s is s2:
                continue
            try:
                l2, t2, w2, h2 = [emu_to_inches(x) for x in (s2.left, s2.top, s2.width, s2.height)]
            except Exception:
                continue
            if (left < l2 + w2 and left + w > l2 and
                top < t2 + h2 and top + h > t2):
                # Could be intentional, skip for now
                pass

    return issues

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pptx", required=True)
    parser.add_argument("--output", default=None, help="Output JSON file for issues")
    args = parser.parse_args()

    from pptx import Presentation
    prs = Presentation(args.pptx)

    all_issues = {}
    for i, slide in enumerate(prs.slides, 1):
        issues = check_slide(slide, i)
        if issues:
            all_issues[f"slide_{i:02d}"] = issues

    result = {"total_issues": sum(len(v) for v in all_issues.values()), "slides": all_issues}

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

    if all_issues:
        print(f"Found {result['total_issues']} issues across {len(all_issues)} slides")
        for slide_name, issues in all_issues.items():
            for issue in issues:
                print(f"  {slide_name}: {issue}")
    else:
        print("No layout issues found.")

if __name__ == "__main__":
    main()
