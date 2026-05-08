"""Render PPTX slides to PNG previews via headless LibreOffice or python-pptx fallback.

Usage:
  python render_slides.py --pptx deck.pptx --output-dir ./preview
"""

import argparse, os, subprocess, sys

def render_libreoffice(pptx_path, output_dir):
    """Use LibreOffice to convert PPTX to PNG."""
    cmd = [
        "soffice", "--headless", "--convert-to", "png",
        "--outdir", output_dir, pptx_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"LibreOffice error: {result.stderr}")
        return False
    return True

def render_gs(pptx_path, output_dir):
    """Use Ghostscript as alternative."""
    try:
        subprocess.run(["gs", "--version"], capture_output=True)
    except FileNotFoundError:
        return False
    # ghostscript-based PDF→PNG chain
    pdf_dir = os.path.join(output_dir, "_pdf")
    os.makedirs(pdf_dir, exist_ok=True)
    subprocess.run([
        "soffice", "--headless", "--convert-to", "pdf",
        "--outdir", pdf_dir, pptx_path
    ], capture_output=True)
    pdf_name = os.path.splitext(os.path.basename(pptx_path))[0] + ".pdf"
    pdf_path = os.path.join(pdf_dir, pdf_name)
    subprocess.run([
        "gs", "-dNOPAUSE", "-dBATCH", "-sDEVICE=png16m",
        "-r150", f"-sOutputFile={output_dir}/slide-%02d.png", pdf_path
    ], capture_output=True)
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pptx", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    if render_libreoffice(args.pptx, args.output_dir):
        print(f"Rendered slides to {args.output_dir}/")
    elif render_gs(args.pptx, args.output_dir):
        print(f"Rendered slides via PDF→PNG to {args.output_dir}/")
    else:
        print("WARNING: No renderer available. Install LibreOffice for slide previews.")

if __name__ == "__main__":
    main()
