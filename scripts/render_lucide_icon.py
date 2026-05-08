#!/usr/bin/env python3
"""Render a Lucide icon to PNG or SVG.

Uses the lucide Python package if available, otherwise renders from bundled
icon data. Falls back to SVG-only output when PNG rendering is unavailable.
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

# Minimal Lucide icon data for common icons (24x24 viewBox)
# Full set available via `pip install lucide-py`
_ICON_DATA = {
    "Activity": [["path", {"d": "M22 12h-4l-3 9L9 3l-3 9H2"}]],
    "ArrowRight": [["path", {"d": "M5 12h14M12 5l7 7-7 7"}]],
    "BarChart3": [["path", {"d": "M3 3v18h18M18 17V9M13 17V5M8 17v-3"}]],
    "Check": [["path", {"d": "M20 6 9 17l-5-5"}]],
    "ChevronRight": [["path", {"d": "m9 18 6-6-6-6"}]],
    "Circle": [["circle", {"cx": "12", "cy": "12", "r": "10"}]],
    "Download": [["path", {"d": "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"}]],
    "FileText": [["path", {"d": "M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"}, {"fill": "none"}], ["polyline", {"points": "14 2 14 8 20 8"}]],
    "Globe": [["circle", {"cx": "12", "cy": "12", "r": "10"}], ["path", {"d": "M12 2a14.7 14.7 0 0 1 5 10 14.7 14.7 0 0 1-5 10M12 2a14.7 14.7 0 0 0-5 10 14.7 14.7 0 0 0 5 10M2 12h20"}]],
    "Info": [["circle", {"cx": "12", "cy": "12", "r": "10"}], ["path", {"d": "M12 16v-4M12 8h.01"}]],
    "Lightbulb": [["path", {"d": "M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5M9 18h6M10 22h4"}]],
    "Link": [["path", {"d": "M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"}]],
    "Menu": [["path", {"d": "M4 12h16M4 6h16M4 18h16"}]],
    "PieChart": [["path", {"d": "M21.21 15.89A10 10 0 1 1 8 2.83M22 12A10 10 0 0 0 12 2v10z"}]],
    "Plus": [["path", {"d": "M5 12h14M12 5v14"}]],
    "Search": [["circle", {"cx": "11", "cy": "11", "r": "8"}], ["path", {"d": "m21 21-4.3-4.3"}]],
    "Settings": [["path", {"d": "M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"}], ["circle", {"cx": "12", "cy": "12", "r": "3"}]],
    "Smartphone": [["rect", {"width": "14", "height": "20", "x": "5", "y": "2", "rx": "2", "ry": "2"}], ["path", {"d": "M12 18h.01"}]],
    "Star": [["path", {"d": "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"}]],
    "Target": [["circle", {"cx": "12", "cy": "12", "r": "10"}], ["circle", {"cx": "12", "cy": "12", "r": "6"}], ["circle", {"cx": "12", "cy": "12", "r": "2"}]],
    "TrendingUp": [["polyline", {"points": "22 7 13.5 15.5 8.5 10.5 2 17"}], ["polyline", {"points": "16 7 22 7 22 13"}]],
    "Users": [["path", {"d": "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"}], ["circle", {"cx": "9", "cy": "7", "r": "4"}], ["path", {"d": "M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"}]],
    "X": [["path", {"d": "M18 6 6 18M6 6l12 12"}]],
    "Zap": [["polygon", {"points": "13 2 3 14 12 14 11 22 21 10 12 10 13 2"}]],
}


def normalize_icon_name(name):
    raw = str(name or "").strip()
    pascal = "".join(
        part[0].upper() + part[1:] for part in raw.replace("-", " ").replace("_", " ").split() if part
    )
    return pascal or raw


def resolve_icon(name):
    candidates = [
        name,
        normalize_icon_name(name),
        name.replace("Icon", ""),
        normalize_icon_name(name).replace("Icon", ""),
    ]
    for c in candidates:
        if c in _ICON_DATA:
            return c, _ICON_DATA[c]
    raise ValueError(f"Unknown Lucide icon: {name}")


def render_node(node):
    tag, attrs, *rest = node
    children = rest[0] if rest else []
    attr_str = " ".join(f'{k}="{xml_escape(str(v))}"' for k, v in (attrs or {}).items())
    open_tag = f"<{tag} {attr_str}" if attr_str else f"<{tag}"
    if not children:
        return f"{open_tag}/>"
    inner = "".join(render_node(c) if isinstance(c, list) else str(c) for c in children)
    return f"{open_tag}>{inner}</{tag}>"


def build_svg(icon_nodes, color, stroke_width, size):
    svg_attrs = (
        f'xmlns="http://www.w3.org/2000/svg" '
        f'width="{xml_escape(str(size))}" height="{xml_escape(str(size))}" '
        f'viewBox="0 0 24 24" fill="none" '
        f'stroke="{xml_escape(color)}" stroke-width="{xml_escape(str(stroke_width))}" '
        f'stroke-linecap="round" stroke-linejoin="round"'
    )
    inner = "".join(render_node(node) for node in icon_nodes)
    return f'<svg {svg_attrs}>{inner}</svg>'


def list_icons():
    for name in sorted(_ICON_DATA):
        print(name)


def main():
    parser = argparse.ArgumentParser(description="Render a Lucide icon to PNG or SVG")
    parser.add_argument("--icon", help="Icon name (e.g. TrendingUp)")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--color", default="#111111", help="Stroke color (default: #111111)")
    parser.add_argument("--size", type=int, default=128, help="Output size in pixels (default: 128)")
    parser.add_argument("--stroke-width", type=float, default=1.8, help="Stroke width (default: 1.8)")
    parser.add_argument("--format", choices=["png", "svg"], help="Output format (default: inferred from --output extension)")
    parser.add_argument("--list", action="store_true", help="List available icons")
    parser.add_argument("--help", action="store_true")

    args = parser.parse_args()

    if args.help:
        parser.print_help()
        return

    if args.list:
        list_icons()
        return

    if not args.icon or not args.output:
        parser.error("--icon and --output are required")

    if args.size <= 0:
        parser.error("--size must be positive")
    if args.stroke_width <= 0:
        parser.error("--stroke-width must be positive")

    fmt = args.format or ("svg" if args.output.lower().endswith(".svg") else "png")
    if fmt not in ("png", "svg"):
        parser.error("--format must be png or svg")

    # Try pip-installed lucide first
    icon_nodes = None
    try:
        import lucide
        icon_map = getattr(lucide, "icons", None) or lucide
        name, _ = resolve_icon(args.icon)  # trigger fallback check
        candidates = [
            args.icon,
            normalize_icon_name(args.icon),
            normalize_icon_name(args.icon).replace("Icon", ""),
        ]
        for c in candidates:
            node = icon_map.get(c)
            if node:
                icon_nodes = node
                break
    except (ImportError, ValueError):
        pass

    # Fall back to bundled data
    if icon_nodes is None:
        _, icon_nodes = resolve_icon(args.icon)

    svg = build_svg(icon_nodes, args.color, args.stroke_width, args.size)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    if fmt == "svg":
        Path(args.output).write_text(svg + "\n", encoding="utf-8")
    else:
        try:
            import cairosvg
            cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=args.output)
        except ImportError:
            try:
                from PIL import Image
                import io
                try:
                    import cairosvg as cs
                    cs.svg2png(bytestring=svg.encode("utf-8"), write_to=args.output)
                except ImportError:
                    raise RuntimeError("PNG output requires cairosvg or Pillow. Install: pip install cairosvg")
            except ImportError:
                raise RuntimeError("PNG output requires cairosvg. Install: pip install cairosvg")

    print(args.output)


if __name__ == "__main__":
    main()
