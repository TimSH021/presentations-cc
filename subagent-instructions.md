# Subagent Instructions

Use this file only when the main agent has explicitly assigned you a bounded
slide or asset task. The main agent owns deck coherence. Your job is to rebuild
the approved reference image into one clean editable python-pptx slide.

Do the following loop exactly:

1. Read the assigned deck brief, source-style audit or style-direction file,
   design-system lock, approved reference image, reference QA notes, source
   notes, icon manifest, and data files before editing.
   For template-following tasks, also read `template-audit.txt`,
   `template-frame-map.json`, `deviation-log.txt`, the relevant source slide
   render, the corresponding source layout JSON, `template-inspect.ndjson`,
   extracted template assets, `template-manifest.json`, and the starter deck
   manifest before editing.
2. Create one Python slide module that exports a single `build(slide, prs)`
   function for your assigned slide.
3. Build a temporary one-slide PPTX by calling only your exported function
   via `build_deck.py`.
4. Render that slide to PNG with `render_slides.py`.
5. Run `python scripts/check_layout.py --pptx <temp.pptx> --output <layout.json>`
   after every render.
6. Compare the rendered PNG to the approved reference image at readable size and
   note a prioritized list of issues, including visual mismatches and any
   layout-quality failures.
7. Repeat from step 2 to fix issues. Repeat this process at least 3 times until
   the slide matches the reference image as well as practical and
   `check_layout.py` has no errors. If exact matching would be worse
   because of factual, legibility, or editability constraints, get as close as
   possible, make it look clean, and document the deviation.
8. If `check_layout.py` reports an error, fix the slide. Do not return
   a slide with checker errors unless the main agent explicitly provided an
   allowlist and written reason.
9. Warnings from `check_layout.py` must be inspected visually. Fix
   warnings involving title/hero gutters, KPI text, split inline text, tight
   text boxes, or text/image collisions unless there is a clear reason not to.
10. Return only your slide module and any cropped/reused assets. Do not return a
    standalone deck as the final artifact.

## Reference Fidelity Rules

1. Use the reference image as a template/layout comp, not loose inspiration.
   Preserve composition, hierarchy, visual rhythm, spacing, color balance, scale,
   and mood where practical.
2. Do not just use the reference image as a background image for the whole slide.
3. Do not replace a strong reference composition with a generic shared layout.
   Shared components are for repeated deck chrome, not for flattening slide bodies.
4. Fix imagegen artifacts: garbled text, fake UI, distorted icons, rough labels,
   bad contrast, decorative clutter, unsupported metrics, and any do-not-rebuild
   elements called out by the main agent.
5. Keep slide copy concise. Do not add paragraphs or extra explanatory text just
   because space exists.

## Template-Following Rules

1. Treat the source deck as the design system unless the main agent explicitly
   says the user requested redesign.
2. For template PPTXs, the assigned slide must come from a duplicated source
   slide in the starter deck. Do not create a fresh theme-matched layout unless
   the main agent documents a rebuild exception.
3. Preserve the assigned source skeleton's title frame, content frame, image
   wells, footers, page markers, decorative chrome, component geometry,
   typography voice, spacing rhythm, and crop language.
4. Fill inherited component slots. Do not place a fresh custom layout on top of
   the template just because it is easier.
5. Classify inherited elements as `keep`, `rewrite`, `replace`, or `delete` and
   keep that classification visible in your return notes.
6. Prefer extracted template assets and crops over new visuals when they are
   part of the intended template language.
7. Record every intentional template deviation with the reason and affected
   element. Unexplained frame drift, missing chrome, blank image wells, and new
   palette/type/surface language are blocking defects.

## Asset and Icon Rules

1. Use vetted brand assets provided by the main agent whenever possible.
2. For generic icons, prefer simple shapes built with python-pptx primitives
   (rectangles, lines, circles) or rendered Lucide icons via
   `render_lucide_icon.py` when available.
3. Do not manually draw icons with lots of shapes or lines when a simple
   geometric equivalent or Lucide icon is close enough.
4. For photos, complex decorative visuals, device mockups, abstract hero art,
   and complex visual effects from the reference comp, crop/reuse the visual
   asset when native reconstruction would be slower or visibly worse.
5. For logos and complex brand marks, use high-quality official assets or clean
   source-provided crops. Do not use rough, fuzzy, distorted, or off-brand crops.
6. Do not use imagegen crops for factual text, chart labels, source notes,
   metrics, or data-bearing UI.
7. Record final icons, logos, and repeated asset marks in the icon manifest with
   source type, icon/library name or asset path, color, size, slide usage,
   approval status, and notes.

## Hard Layout Rules

1. Declare layout zones before drawing. Use constants such as `SAFE_LEFT`,
   `HEADER_TOP`, `FOOTER_BOTTOM`, `TEXT_ZONE`, `VISUAL_ZONE`, `CHART_ZONE`, and
   `KPI_ZONE`. Keep all major text, KPI cards, charts, and hero visuals inside
   their assigned zones.
2. No major text box may overlap a hero image, diagram, chart, table, or visual
   zone unless the prompt explicitly asks for text-over-image.
3. Leave at least 24px (Inches(0.25)) of gutter between major text blocks and
   hero images/diagrams/charts.
4. Do not split a single sentence across multiple text boxes just to style one
   phrase. Use one text box with separate paragraphs.
5. KPI cards must reserve separate vertical slots for label, value, suffix, and
   note. Leave enough room for font fallback.
6. Treat font fallback as normal. Every text box needs slack: at least 10-20%
   extra width and height beyond the expected text.
7. Cropped images must be placed in aspect-ratio-compatible frames unless
   intentionally masked.
8. Do not invent quantitative claims. Every number must be sourced from the
   prompt/source notes, derived transparently, or omitted.

## Kicker Convention

Use named kicker pairs so QA can verify centerline alignment:

```python
# Marker
marker = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(0.1), Inches(0.1))
marker.name = "kicker-marker"

# Label
label = slide.shapes.add_textbox(Inches(x + 0.22), Inches(y - 0.02), Inches(3), Inches(0.3))
label.name = "kicker-label"
```

The marker center and label center must share the same y coordinate within <= 1px.

## Slide Module Format

Your module must look like this:

```python
def build(slide, prs):
    """Build slide NN: [narrative role].

    slide: pptx.slide.Slide
    prs: pptx.Presentation
    """
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE

    # Background
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(0xF7, 0xF2, 0xEA)

    # Kicker
    marker = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.58), Inches(0.48), Inches(0.14), Inches(0.14))
    marker.name = "kicker-marker"
    marker.fill.solid()
    marker.fill.fore_color.rgb = RGBColor(0x17, 0x6B, 0x87)
    marker.line.fill.background()

    label = slide.shapes.add_textbox(Inches(0.82), Inches(0.48), Inches(3), Inches(0.22))
    label.name = "kicker-label"
    tf = label.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "SECTION NAME"
    p.font.size = Pt(9.5)
    p.font.color.rgb = RGBColor(0x68, 0x73, 0x86)
    p.font.bold = True

    # Claim title
    # Proof object
    # Footer / page marker

    return slide
```

## Key Differences From Codex

If you are familiar with the Codex Presentations plugin:

- `export async function slide01(presentation, ctx)` → `def build(slide, prs):`
- `ctx.addText(slide, {...})` → `slide.shapes.add_textbox(...)` + text_frame setup
- `ctx.addShape(slide, {...})` → `slide.shapes.add_shape(...)` + fill/line setup
- `ctx.addLucideIcon(slide, {...})` → render icon PNG with `render_lucide_icon.py`, then `slide.shapes.add_picture(...)`
- `Presentation.create({slideSize})` → `Presentation()` with `slide_width` / `slide_height` in Emu
- `render_artifact_slide.mjs` → `build_deck.py` + `render_slides.py`
- `check_layout_quality.mjs` → `check_layout.py`
- Slide size is in inches (13.333×7.5 for 16:9), not pixels (1280×720)
