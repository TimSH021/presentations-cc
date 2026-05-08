#!/usr/bin/env python3
"""Write an imagegen prompt text file (no API call — agent handles the actual generation).

Adapted from OpenAI Codex openai_generate_image.py.
"""

import argparse, json
from datetime import datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("-o", "--output", help="Intended image path (not created by this script)")
    parser.add_argument("--prompt-output", help="Prompt file path")
    parser.add_argument("--reference-image")
    parser.add_argument("--size", default="1792x1024")
    parser.add_argument("--quality", default="medium")
    parser.add_argument("--format", dest="output_format", default="png")
    parser.add_argument("--background", default="auto")
    parser.add_argument("--moderation", default="auto")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    # Resolve reference image
    ref = None
    if args.reference_image:
        ref = Path(args.reference_image).expanduser().resolve()
        if not ref.exists():
            raise FileNotFoundError(f"Reference image not found: {ref}")

    # Resolve prompt output path
    if args.prompt_output:
        prompt_path = Path(args.prompt_output).expanduser().resolve()
    elif args.output:
        prompt_path = Path(args.output).expanduser().resolve().with_suffix(".imagegen.txt")
    else:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        prompt_path = Path.cwd() / f"imagegen-prompt-{stamp}.txt"

    if prompt_path.exists() and not args.force:
        raise FileExistsError(f"Prompt file exists: {prompt_path}")

    intended = str(Path(args.output).expanduser().resolve()) if args.output else ""
    metadata = {
        "intended_output": intended,
        "reference_image": str(ref) if ref else "",
        "size": args.size,
        "quality": args.quality,
        "format": args.output_format,
        "background": args.background,
        "moderation": args.moderation,
    }

    doc = "\n".join([
        "# Image Generation Prompt",
        "",
        "Generate an image from this prompt. Do not call external image APIs from scripts.",
        "",
        "```json",
        json.dumps(metadata, indent=2),
        "```",
        "",
        "## Prompt",
        "",
        args.prompt.strip(),
        "",
    ])

    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(doc, encoding="utf-8")

    result = {
        "prompt_output": str(prompt_path),
        "intended_output": intended,
        "reference_image": str(ref) if ref else "",
        "imagegen_required": True,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
