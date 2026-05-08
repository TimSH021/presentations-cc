# presentations-cc

Claude Code skill — build premium, narrative-driven PPTX decks with python-pptx. Distilled from the OpenAI Codex Presentations plugin.

## Features

- **9-phase workflow**: task mode → profile routing → source audit → claim spine → design system → contact sheet → build → comeback rubric → iterate
- **8 industry profiles**: product-platform, finance-ir, gtm-growth, engineering-platform, strategy-leadership, consumer-retail, template-and-edit, appendix-heavy
- **Comeback rubric** (0-50 scoring): story, specificity, rhythm, whitespace, chart clarity, typography, restraint, precision, coherence
- **Anti-pattern guardrails**: 25+ blocking anti-patterns that must be fixed before delivery

## Quick Start

```bash
# Install as Claude Code skill
ln -s $(pwd) ~/.claude/skills/presentations-cc
```

Then invoke in Claude Code: `/presentations-cc` or just describe your PPT task.

## Scripts

| Script | Purpose |
|--------|---------|
| `build_deck.py` | Assemble slides into PPTX |
| `render_slides.py` | Render PPTX to PNG previews |
| `check_layout.py` | Layout quality check |
| `contact_sheet.py` | Generate thumbnail overview |
| `inspect_template.py` | Extract template metadata |
| `cleanup.py` | Clean workspace, keep PPTX |
| `imagegen_prompt.py` | Write image generation prompts |

## Requirements

- Python 3.9+
- python-pptx
- Pillow
