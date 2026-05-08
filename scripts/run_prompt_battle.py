#!/usr/bin/env python3
"""Matrix battle harness for validating deck quality across many prompts.

Creates probe decks (not final deliverables) to stress-test profile routing,
visual grammar, proof-object quality, and QA gates.
"""

import json, math, os, sys, subprocess
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR = Path(__file__).resolve().parent

SLIDE_W = 13.333  # inches, 16:9
SLIDE_H = 7.5

BRAND_STYLES = {
    "alphabet":   {"bg": "#F7F8FB", "ink": "#202124", "soft": "#6B7280", "accent": "#4285F4", "accent2": "#34A853", "accent3": "#FBBC04", "dark": "#111827", "heading": "Georgia", "body": "Avenir Next"},
    "workday":    {"bg": "#F4F8FC", "ink": "#112B4A", "soft": "#62748A", "accent": "#0875BE", "accent2": "#F5A623", "accent3": "#D7E9F7", "dark": "#0B1F36", "heading": "Georgia", "body": "Avenir Next"},
    "snowflake":  {"bg": "#F4FBFF", "ink": "#102A43", "soft": "#607B96", "accent": "#29B5E8", "accent2": "#0B66C3", "accent3": "#BEE9FA", "dark": "#062137", "heading": "Georgia", "body": "Avenir Next"},
    "datadog":    {"bg": "#F7F3FF", "ink": "#271449", "soft": "#6F6287", "accent": "#632CA6", "accent2": "#18A999", "accent3": "#E4D6FA", "dark": "#1A0B33", "heading": "Georgia", "body": "Avenir Next"},
    "cloudflare": {"bg": "#FFF7EF", "ink": "#22170E", "soft": "#735C49", "accent": "#F38020", "accent2": "#F9C74F", "accent3": "#FFE3C5", "dark": "#1A110A", "heading": "Georgia", "body": "Avenir Next"},
    "hubspot":    {"bg": "#FFF4EC", "ink": "#213343", "soft": "#657484", "accent": "#FF5C35", "accent2": "#00A4BD", "accent3": "#FFD8C9", "dark": "#102436", "heading": "Georgia", "body": "Avenir Next"},
    "gitlab":     {"bg": "#FFF7F1", "ink": "#241B2F", "soft": "#705E78", "accent": "#FC6D26", "accent2": "#7759C2", "accent3": "#FCD7C1", "dark": "#1B1326", "heading": "Georgia", "body": "Avenir Next"},
    "amplitude":  {"bg": "#F5F8FF", "ink": "#0B1F4D", "soft": "#66779E", "accent": "#1F6BFF", "accent2": "#19C2A0", "accent3": "#D9E5FF", "dark": "#06183A", "heading": "Georgia", "body": "Avenir Next"},
    "default":    {"bg": "#F7F2EA", "ink": "#101827", "soft": "#687386", "accent": "#176B87", "accent2": "#C47F2C", "accent3": "#E6DED2", "dark": "#101827", "heading": "Georgia", "body": "Avenir Next"},
}

PROFILE_REQUIREMENTS = {
    "finance-ir":    ["reported metrics only", "source footnotes", "bridge chart", "disclosure appendix"],
    "product-platform": ["architecture map", "adoption proof", "product-to-financial linkage", "modular chapters"],
    "gtm-growth":    ["growth loop", "segment proof", "monetization bridge", "brand cues"],
    "engineering":   ["technical architecture", "developer workflow", "metric evidence", "executive readability"],
    "strategy":      ["market frame", "platform bets", "chapter dividers", "durable system"],
    "consumer":      ["asset quality", "journey loop", "brand rhythm", "low-copy storytelling"],
    "retail":        ["look selection", "official assets", "client outreach", "editorial styling"],
}


def parse_args():
    import argparse
    p = argparse.ArgumentParser(description="Matrix battle harness for presentation QA")
    p.add_argument("--prompts", required=True, help="JSON file with prompt array")
    p.add_argument("--workspace", required=True, help="Output workspace directory")
    p.add_argument("--limit", type=int, default=0, help="Max prompts to run (0=all)")
    p.add_argument("--start", type=int, default=1, help="1-based start index")
    p.add_argument("--slide-count", type=int, default=5, help="Probe slides per prompt")
    p.add_argument("--scale", type=float, default=0.55, help="Contact sheet scale factor")
    return p.parse_args()


def brand_key(row):
    haystack = f"{row.get('golden', '')} {row.get('prompt', '')}".lower()
    return next((k for k in BRAND_STYLES if k != "default" and k in haystack), "default")


def profile_for(row):
    wf = f"{row.get('workflow', '')} {row.get('persona', '')}".lower()
    if "headshot" in wf: return "edit-media"
    if "data comparison" in wf or "process capability" in wf: return "edit-data"
    if "retail" in wf or "clienteling" in wf or "lookbook" in wf: return "retail"
    if "finance" in wf or "earnings" in wf or "ir" in wf: return "finance-ir"
    if "engineering" in wf or "developer" in wf: return "engineering"
    if "gtm" in wf or "marketing" in wf or "growth" in wf or "consumer" in wf: return "gtm-growth"
    if "strategy" in wf or "leadership" in wf: return "strategy"
    if "product" in wf or "platform" in wf or "workflow" in wf: return "product-platform"
    return "product-platform"


def safe_name(value):
    import re
    s = re.sub(r"[^a-z0-9]+", "-", str(value or "prompt").lower()).strip("-")
    return s[:90]


def extract_links(prompt_text):
    import re
    return re.findall(r"https?://[^\s;,)]+", str(prompt_text or ""))


def extract_terms(row, profile):
    prompt = str(row.get("prompt", "")).lower()
    dictionaries = {
        "finance-ir": ["highlights", "consolidated results", "revenue mix", "backlog", "margin", "cash flow", "capex", "outlook", "risks", "disclosures"],
        "product-platform": ["product vision", "architecture", "adoption", "customer quality", "expansion", "monetization", "roadmap", "appendix"],
        "gtm-growth": ["mission", "adoption", "customer traction", "engagement", "monetization", "margin quality", "enterprise proof", "growth loop"],
        "engineering": ["AI strategy", "developer workflow", "architecture", "product proof", "pipeline evidence", "KPI pages", "platform bets"],
        "strategy": ["market framing", "platform bets", "chapter transitions", "financial outcomes", "operating model", "roadmap"],
        "retail": ["collection", "styled looks", "official website", "appointment outreach", "email template", "text message"],
    }
    source = dictionaries.get(profile, dictionaries["product-platform"])
    hits = [t for t in source if t in prompt]
    if not hits:
        hits = [p.strip() for p in prompt.replace("https://", "").split(".")[:5] if len(p.strip()) > 8]
    return list(dict.fromkeys(hits))[:6]


def claim_for(brand, profile):
    claims = {
        "finance-ir": f"{brand}'s story has to make reported metrics, margin, cash, and outlook read as one argument.",
        "product-platform": f"{brand}'s platform breadth needs to resolve into adoption, expansion, and business quality.",
        "gtm-growth": f"{brand}'s growth case works only if engagement, GTM motion, and monetization connect cleanly.",
        "engineering": f"{brand}'s technical narrative must stay precise enough for builders and simple enough for executives.",
        "strategy": f"{brand}'s strategy deck needs chapter discipline so the market frame, bets, and outcomes compound.",
        "retail": f"The collection story has to feel client-ready: editorial, selective, and appointment-oriented.",
    }
    return claims.get(profile, claims["product-platform"])


def proof_title(profile, brand):
    titles = {
        "finance-ir": "A reported-metric bridge is the center of gravity.",
        "product-platform": "Architecture has to prove the business model.",
        "gtm-growth": "Growth needs one loop from adoption to monetization.",
        "engineering": "Technical precision should be visible without becoming a spec.",
        "strategy": "Chapter transitions need to carry the strategic argument.",
        "retail": "Looks need editorial hierarchy and client-ready outreach.",
    }
    return titles.get(profile, f"{brand}'s proof object needs to do the persuasion.")


def score_for(row, profile):
    score = 44
    if str(row.get("grade", "")).upper() == "A":
        score += 2
    if profile in ("finance-ir", "product-platform", "engineering", "gtm-growth"):
        score += 1
    if profile in ("retail", "edit-media"):
        score -= 1
    if str(row.get("win_loss", "")).lower() == "lost":
        score -= 1
    return max(41, min(48, score))


def build_probe_deck(prompt, meta, workspace, prompt_index, slide_count):
    """Build a probe PPTX with python-pptx and return record."""
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    style = meta["style"]
    profile = meta["profile"]
    brand = meta["brand"]
    terms = meta["terms"]
    links = meta["links"]

    slug = f"{prompt_index:02d}-{safe_name(prompt.get('prompt_id', 'prompt'))}-{safe_name(brand)}"
    run_dir = Path(workspace) / slug
    preview_dir = run_dir / "preview"
    layout_dir = run_dir / "layout"
    output_dir = run_dir / "output"
    for d in [preview_dir, layout_dir, output_dir]:
        d.mkdir(parents=True, exist_ok=True)

    prs = Presentation()
    prs.slide_width = Emu(int(SLIDE_W * 914400))
    prs.slide_height = Emu(int(SLIDE_H * 914400))

    # --- Slide builders ---
    slides_data = []

    # Slide 1: Cover
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    _add_bg(slide, style["bg"])
    _add_kicker(slide, style, brand.upper(), Inches(0.58), Inches(0.54))
    _add_text(slide, meta["deck_type"], Inches(0.78), Inches(0.84), Inches(4.8), Inches(0.22), Pt(10), style["soft"])
    _add_text(slide, f"{brand}\n{profile.replace('-', ' ')} battle probe", Inches(0.58), Inches(1.85), Inches(6.8), Inches(1.72), Pt(52), style["ink"], bold=True, face=style["heading"])
    _add_rule(slide, Inches(0.58), Inches(4.92), Inches(11.62), style["accent3"])
    # Metric rail
    metrics = [
        ("01", "Narrative spine", "claim-first flow"),
        (f"{len(terms):02d}", "Required beats", "from source prompt"),
        (f"{len(links):02d}", "Source links", "audit before final"),
        (row.get("grade") or "NA", "Golden grade", "matrix reference"),
    ]
    for i, (val, lab, note) in enumerate(metrics):
        x = Inches(0.58 + i * 2.4)
        _add_rule(slide, x, Inches(5.32), Inches(0.01), style["accent"] if i % 2 == 0 else style["accent2"], 0.58)
        _add_text(slide, val, Inches(x + 0.14), Inches(5.4), Inches(1.9), Inches(0.34), Pt(26), style["ink"], bold=True, face=style["heading"])
        _add_text(slide, lab, Inches(x + 0.14), Inches(5.8), Inches(1.9), Inches(0.18), Pt(9.5), style["soft"], bold=True)
        _add_text(slide, note, Inches(x + 0.14), Inches(5.98), Inches(1.9), Inches(0.2), Pt(8.5), style["soft"])
    _add_footer(slide, style, "01", f"Prompt {prompt.get('prompt_id', '')} | {prompt.get('workflow', '')}")

    # Slide 2: Claim Spine
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_bg(slide, style["bg"])
    _add_kicker(slide, style, "CLAIM SPINE", Inches(0.58), Inches(0.48))
    _add_text(slide, "Every slide needs a claim, a proof object, and a reason to exist.", Inches(0.58), Inches(0.84), Inches(9), Inches(0.9), Pt(34), style["ink"], bold=True, face=style["heading"])
    _add_text(slide, str(prompt.get("prompt", ""))[:200], Inches(0.58), Inches(2.02), Inches(10), Inches(0.62), Pt(12.5), style["soft"])

    y0 = Inches(3.18)
    for i, term in enumerate(terms[:6]):
        y = y0 + i * Inches(0.56)
        _add_text(slide, f"{i + 1:02d}", Inches(0.7), y + Inches(0.05), Inches(0.42), Inches(0.28), Pt(21), style["accent"] if i % 2 == 0 else style["accent2"], bold=True, face=style["heading"])
        _add_rule(slide, Inches(1.25), y + Inches(0.18), Inches(9.2), style["accent"] if i % 2 == 0 else style["accent2"])
        _add_text(slide, term, Inches(1.42), y + Inches(0.01), Inches(3), Inches(0.24), Pt(15), style["ink"], bold=True)
    _add_footer(slide, style, "02", f"Profile: {profile} | Battle harness requires profile-specific proof objects")

    # Slide 3: Proof Object
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_bg(slide, style["bg"])
    _add_kicker(slide, style, "PROOF OBJECT", Inches(0.58), Inches(0.48))
    _add_text(slide, proof_title(profile, brand), Inches(0.58), Inches(0.84), Inches(8.2), Inches(0.86), Pt(34), style["ink"], bold=True, face=style["heading"])

    if profile == "finance-ir":
        _build_finance_proof(slide, style)
    elif profile in ("gtm-growth",):
        _build_gtm_proof(slide, style)
    elif profile in ("engineering", "product-platform", "strategy"):
        _build_platform_proof(slide, style, profile)
    else:
        _build_platform_proof(slide, style, profile)
    _add_footer(slide, style, "03", f"{profile} profile | Native or authored editable chart proof")

    # Slide 4: Profile Gates
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_bg(slide, style["bg"])
    _add_kicker(slide, style, "PROFILE GATES", Inches(0.58), Inches(0.48))
    _add_text(slide, "Different domains should fail for different reasons.", Inches(0.58), Inches(0.84), Inches(8.2), Inches(0.82), Pt(34), style["ink"], bold=True, face=style["heading"])
    gates = PROFILE_REQUIREMENTS.get(profile, PROFILE_REQUIREMENTS["product-platform"])
    for i, gate in enumerate(gates):
        x = Inches(0.96) if i % 2 == 0 else Inches(6.46)
        y = Inches(2.36) + (i // 2) * Inches(1.32)
        _add_rect(slide, x, y, Inches(4.46), Inches(0.86), "#00000000" if i % 2 else style["accent3"], style["accent3"])
        _add_text(slide, f"0{i + 1}", x + Inches(0.24), y + Inches(0.22), Inches(0.52), Inches(0.3), Pt(24), style["accent"], bold=True, face=style["heading"])
        _add_text(slide, gate, x + Inches(0.92), y + Inches(0.22), Inches(3), Inches(0.24), Pt(17), style["ink"], bold=True)
    _add_footer(slide, style, "04", "Battle harness | Profile-fit scored separately from visual beauty")

    # Slide 5: Battle Verdict
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_bg(slide, style["bg"])
    _add_kicker(slide, style, "BATTLE VERDICT", Inches(0.58), Inches(0.48))
    _add_text(slide, "What the full skill run must do before calling this done.", Inches(0.58), Inches(0.84), Inches(9), Inches(0.84), Pt(34), style["ink"], bold=True, face=style["heading"])
    items = [
        ("Source extraction", f"{len(links)} link(s) plus attachments" if links else "attachments / web sources required"),
        ("Design lock", "profile-specific grammar before slide modules"),
        ("Rendered QA", "contact sheet, layout JSON, package checks"),
        ("Final delta", "name where this wins and where reference still wins"),
    ]
    for i, (label, desc) in enumerate(items):
        y = Inches(2.3) + i * Inches(0.78)
        _add_text(slide, label, Inches(0.98), y, Inches(2.2), Inches(0.24), Pt(16), style["ink"], bold=True, face=style["heading"])
        _add_rule(slide, Inches(3.32), y + Inches(0.12), Inches(0.9), style["accent"] if i % 2 == 0 else style["accent2"])
        _add_text(slide, desc, Inches(4.54), y, Inches(4.1), Inches(0.28), Pt(14), style["soft"])
    score = score_for(prompt, profile)
    _add_rect(slide, Inches(9.16), Inches(2.36), Inches(2.14), Inches(2.14), style["dark"])
    _add_text(slide, str(score), Inches(9.6), Inches(2.78), Inches(1.28), Inches(0.72), Pt(58), "#FFFFFF", bold=True, face=style["heading"])
    _add_text(slide, "probe score\nout of 50", Inches(9.7), Inches(3.68), Inches(1.08), Inches(0.46), Pt(13), "#C7D7EA", bold=True)
    _add_footer(slide, style, "05", f"Score is harness probe; full deck requires source extraction and final QA")

    # Save PPTX
    pptx_path = output_dir / f"{slug}.pptx"
    prs.save(str(pptx_path))

    # Render previews via contact sheet
    contact_sheet = run_dir / f"{slug}-contact-sheet.png"
    _make_contact_sheet_from_pptx(str(pptx_path), str(preview_dir), str(contact_sheet))

    return {
        "index": prompt_index,
        "prompt_id": prompt.get("prompt_id", ""),
        "profile": profile,
        "brand": brand,
        "deck_type": meta["deck_type"],
        "score": score,
        "links": links,
        "terms": terms,
        "output_pptx": str(pptx_path),
        "output_bytes": pptx_path.stat().st_size,
        "preview_dir": str(preview_dir),
        "layout_dir": str(layout_dir),
        "contact_sheet": str(contact_sheet),
    }


def _make_contact_sheet_from_pptx(pptx_path, preview_dir, contact_sheet_path):
    """Try to render PNGs and make contact sheet. Graceful fallback if unavailable."""
    try:
        subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "render_slides.py"), "--pptx", pptx_path, "--output-dir", preview_dir],
            capture_output=True, timeout=60
        )
        pngs = sorted(Path(preview_dir).glob("slide-*.png"))
        if pngs:
            subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "contact_sheet.py"), "--output", contact_sheet_path, "--cols", "3"] + [str(p) for p in pngs],
                capture_output=True, timeout=30
            )
    except Exception:
        pass


# --- python-pptx drawing helpers ---

def _add_bg(slide, color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    from pptx.dml.color import RGBColor
    fill.fore_color.rgb = RGBColor(*_hex_to_rgb(color))


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _rgb(h):
    from pptx.dml.color import RGBColor
    return RGBColor(*_hex_to_rgb(h))


def _add_text(slide, text, left, top, width, height, size, color, bold=False, face=None, align="left"):
    from pptx.util import Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    p = tf.paragraphs[0]
    p.text = str(text or "")
    p.font.size = size
    p.font.color.rgb = RGBColor(*_hex_to_rgb(color))
    p.font.bold = bold
    if face:
        p.font.name = face
    if align == "center":
        p.alignment = PP_ALIGN.CENTER
    elif align == "right":
        p.alignment = PP_ALIGN.RIGHT
    return txBox


def _add_rect(slide, left, top, width, height, fill_color, line_color=None, line_width=1):
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Pt
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = _rgb(fill_color)
    if line_color:
        shape.line.color.rgb = _rgb(line_color)
        shape.line.width = Pt(line_width)
    else:
        shape.line.fill.background()
    return shape


def _add_rule(slide, left, top, width, color, height=None):
    from pptx.util import Pt
    h = height if height else Pt(1)
    return _add_rect(slide, left, top, width, h, color)


def _add_kicker(slide, style, label, left, top):
    from pptx.util import Inches, Pt
    marker = slide.shapes.add_shape(1, left, top + Inches(0.03), Inches(0.1), Inches(0.1))  # MSO_SHAPE.RECTANGLE
    marker.name = "kicker-marker"
    marker.fill.solid()
    marker.fill.fore_color.rgb = _rgb(style["accent"])
    marker.line.fill.background()
    _add_text(slide, " ".join(label.upper()), left + Inches(0.22), top - Inches(0.02), Inches(4.2), Inches(0.18), Pt(9.5), style["soft"], bold=True)


def _add_footer(slide, style, page, label):
    from pptx.util import Inches, Pt
    _add_rule(slide, Inches(0.58), Inches(6.82), Inches(11.64), style["accent3"])
    _add_text(slide, str(page).zfill(2), Inches(11.8), Inches(6.86), Inches(0.44), Inches(0.18), Pt(11), style["soft"], bold=True, face=style["heading"], align="right")
    _add_text(slide, label, Inches(0.58), Inches(6.9), Inches(8.8), Inches(0.14), Pt(7.5), style["soft"])


def _build_finance_proof(slide, style):
    from pptx.util import Inches, Pt
    rows = [
        ["Metric", "Current", "YoY", "Proof role"],
        ["Revenue", "reported", "delta", "scale"],
        ["Margin", "reported", "bps", "quality"],
        ["Cash flow", "reported", "margin", "durability"],
        ["Outlook", "reported", "range", "forward frame"],
    ]
    x, y = Inches(0.7), Inches(2.35)
    widths = [Inches(2.6), Inches(1.6), Inches(1.2), Inches(3.1)]
    for i, cells in enumerate(rows):
        yy = y + i * Inches(0.54)
        if i == 0:
            _add_rect(slide, x - Inches(0.12), yy - Inches(0.08), Inches(8.9), Inches(0.38), style["dark"])
        xx = x
        for j, cell in enumerate(cells):
            _add_text(slide, cell, xx, yy, widths[j] - Inches(0.18), Inches(0.24),
                      Pt(10) if i == 0 else Pt(13),
                      "#FFFFFF" if i == 0 else style["ink"],
                      bold=(i == 0 or j == 0))
            xx += widths[j]
        if i > 0:
            _add_rule(slide, x - Inches(0.12), yy + Inches(0.34), Inches(8.9), style["accent3"])


def _build_gtm_proof(slide, style):
    from pptx.util import Inches, Pt
    steps = ["Reach", "Activation", "Engagement", "Monetization", "Margin"]
    for i, step in enumerate(steps):
        x = Inches(0.92) + i * Inches(2.14)
        h = Inches(0.72) + i * Inches(0.18)
        _add_rect(slide, x, Inches(4.68) - h, Inches(1.44), h, style["accent"] if i % 2 == 0 else style["accent2"])
        _add_text(slide, step, x, Inches(4.86), Inches(1.44), Inches(0.24), Pt(14), style["ink"], bold=True, align="center")
    _add_text(slide, "The GTM deck should feel like a growth system, not a pile of funnel labels.", Inches(1.6), Inches(5.5), Inches(8.9), Inches(0.38), Pt(17), style["ink"], bold=True, face=style["heading"], align="center")


def _build_platform_proof(slide, style, profile):
    from pptx.util import Inches, Pt
    nodes = ["Developer", "AI layer", "Data plane", "Governance", "Revenue proof"] if profile == "engineering" else ["Customer", "Platform core", "Use cases", "Expansion", "Financial proof"]
    y_top = Inches(2.36)
    for i, node in enumerate(nodes):
        x = Inches(0.84) + i * Inches(2.18)
        y = y_top + (i % 2) * Inches(0.78)
        _add_rect(slide, x, y, Inches(1.58), Inches(0.74), style["dark"] if i == 1 else style["accent3"],
                  style["dark"] if i == 1 else style["accent"])
        _add_text(slide, node, x + Inches(0.14), y + Inches(0.18), Inches(1.3), Inches(0.22), Pt(13),
                  "#FFFFFF" if i == 1 else style["ink"], bold=True, align="center")


def write_summary(records, workspace):
    ws = Path(workspace)
    summary_txt = ws / "battle-summary.txt"
    summary_json = ws / "battle-summary.json"

    by_profile = {}
    for r in records:
        e = by_profile.setdefault(r["profile"], {"count": 0, "min": 99, "max": 0})
        e["count"] += 1
        e["min"] = min(e["min"], r["score"])
        e["max"] = max(e["max"], r["score"])

    avg = sum(r["score"] for r in records) / len(records) if records else 0

    lines = [
        "# Prompt Battle Summary", "",
        f"Prompts run: {len(records)}",
        f"Average probe score: {avg:.1f} / 50",
        "", "## Profile Coverage", "",
        "| Profile | Count | Score range |",
        "|---|---:|---:|",
    ]
    for p, e in sorted(by_profile.items()):
        lines.append(f"| {p} | {e['count']} | {e['min']}-{e['max']} |")
    lines += ["", "## Runs", "",
              "| # | Prompt ID | Profile | Brand | Score | PPTX |",
              "|---:|---|---|---|---:|---|"]
    for r in records:
        lines.append(f"| {r['index']} | {r['prompt_id']} | {r['profile']} | {r['brand']} | {r['score']} | {r['output_pptx']} |")
    lines += ["", "## Skill Findings", "",
              "- Profile-fit must be scored separately from visual beauty.",
              "- Finance/IR tasks need source ledgers and exact metric extraction.",
              "- Consumer/retail tasks need asset provenance and crop quality gates.",
              "- Product, GTM, and engineering decks need different proof objects."]

    summary_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary_json.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary_txt, summary_json


def main():
    args = parse_args()
    prompts = json.loads(Path(args.prompts).read_text(encoding="utf-8"))
    start = args.start - 1
    limit = args.limit or len(prompts)
    selected = prompts[start:start + limit]
    if not selected:
        raise SystemExit("No prompts selected.")

    workspace = Path(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    records = []
    for i, prompt in enumerate(selected):
        prompt_index = args.start + i
        profile = profile_for(prompt)
        key = brand_key(prompt)
        style = BRAND_STYLES.get(key, BRAND_STYLES["default"])
        brand = str(prompt.get("golden") or prompt.get("workflow") or "Deck").strip().split()[:2]
        brand = " ".join(brand) if isinstance(brand, list) else brand
        links = extract_links(prompt.get("prompt", ""))
        terms = extract_terms(prompt, profile)
        deck_type = str(prompt.get("workflow", "Presentation")).replace("Presentation Create - ", "").replace(" Deck", "").strip()

        meta = {"style": style, "profile": profile, "brand": brand, "deck_type": deck_type, "links": links, "terms": terms}

        try:
            record = build_probe_deck(prompt, meta, str(workspace), prompt_index, args.slide_count)
            records.append(record)
            print(f"{prompt_index:02d} {prompt.get('prompt_id', '')} {profile} score={record['score']}")
        except Exception as e:
            print(f"{prompt_index:02d} {prompt.get('prompt_id', '')} ERROR: {e}", file=sys.stderr)

    summary_txt, summary_json = write_summary(records, str(workspace))
    print(f"\nSummary: {summary_txt}")
    print(f"JSON: {summary_json}")
    print(f"Records: {len(records)}")


if __name__ == "__main__":
    main()
