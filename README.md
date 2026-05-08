# presentations-cc

[English](#english) | [中文](#中文)

Build premium, narrative-driven PPTX decks with python-pptx for Claude Code.
Distilled from the OpenAI Codex Presentations plugin.

GitHub: [github.com/TimSH021/presentations-cc](https://github.com/TimSH021/presentations-cc)

---

## 中文

### 简介

presentations-cc 是一个 Claude Code 技能，用 python-pptx 构建高质量商业演示文稿。蒸馏自 OpenAI Codex Presentations 插件（26.506.11943 版本）。

### 功能

- **完整工作流**：任务模式 → 源素材审计 → 叙事脊柱 → 设计系统锁定 → 联系表规划 → 构建 → 回归评分 → 迭代 → 交付
- **7 个行业 Profile**：finance-ir / product-platform / gtm-growth / engineering-platform / consumer-retail / template-and-edit / appendix-heavy
- **Comeback Rubric** 0-50 评分体系，9 个维度
- **25+ 阻断性反模式**，交付前必须修复
- **模板继承工作流**：复制→编辑→保持一致性
- **结构化视觉精度合约**：连接器、图表、容器语法规则

### 快速开始

```bash
# 安装为 Claude Code skill
cd ~/.claude/skills
git clone https://github.com/TimSH021/presentations-cc.git

# 在 Claude Code 中调用
/presentations-cc
```

### 依赖

- Python 3.9+
- python-pptx
- Pillow

### 脚本

| 脚本 | 用途 |
|------|------|
| `build_deck.py` | 将 slide 模块组装成 PPTX |
| `render_slides.py` | PPTX 渲染为 PNG 预览 |
| `check_layout.py` | 布局质量检查 |
| `contact_sheet.py` | 生成缩略图概览 |
| `cleanup.py` | 清理工作区，保留 PPTX |
| `inspect_template.py` | 提取模板元数据 |
| `prepare_starter_deck.py` | 复制模板幻灯片构建起始 deck |
| `imagegen_prompt.py` | 生成图像生成提示文件 |
| `create_reference_slide.py` | 单页参考幻灯片提示生成 |
| `create_reference_slides.py` | 批量参考幻灯片提示生成 |
| `render_lucide_icon.py` | 渲染 Lucide 图标为 PNG/SVG |
| `check_icon_manifest.py` | 验证图标清单 JSON |
| `run_prompt_battle.py` | 批量提示矩阵对战测试 |

### 项目结构

```
presentations-cc/
├── SKILL.md              # 技能定义
├── README.md             # 本文件
├── subagent-instructions.md  # 子 agent 指令
├── profiles/             # 行业 profile 定义 (7个)
├── scripts/              # 工具脚本 (13个)
└── templates/            # 模板 (3个)
```

---

## English

### Overview

presentations-cc is a Claude Code skill for building premium, editable PPTX
presentation decks using python-pptx. It was distilled from the OpenAI Codex
Presentations plugin (version 26.506.11943) and adapted to work without the
Codex artifact-tool runtime.

### Features

- **Full workflow**: task mode → source audit → claim spine → design system lock → contact sheet → build → comeback rubric → iterate → deliver
- **7 industry profiles** with domain-specific proof objects and QA gates
- **Comeback Rubric**: 0-50 scoring across 9 dimensions
- **25+ blocking anti-patterns** that must be fixed before delivery
- **Template-following workflow** with duplicate-first methodology
- **Structured Visual Precision Contract** for charts, connectors, and box systems

### Installation

```bash
# Clone and install as Claude Code skill
cd ~/.claude/skills
git clone https://github.com/TimSH021/presentations-cc.git

# Invoke in Claude Code
/presentations-cc
```

### For AI Agents

This skill provides a complete, production-ready pipeline for building PPTX decks.
Here is how to use it effectively:

1. **Route first**: Read the user's request, determine the task mode (create /
   reference-beating / template-following / targeted-edit), then select the
   primary deck profile from `profiles/`. This determines which proof objects
   and QA gates are blocking.

2. **Read the profile**: Before building, read the relevant profile file under
   `profiles/`. Each profile defines hard gates, required proof objects, and
   failure signs specific to the domain.

3. **Follow the workflow in SKILL.md**: The mandatory workflow is defined in
   `SKILL.md`. Do not skip phases. The claim spine (Phase 1) is binding — write
   the story before designing slides.

4. **Build with python-pptx**: Each slide is a `slide_NN.py` file exporting a
   `build(slide, prs)` function. Use `build_deck.py` to assemble, `render_slides.py`
   to preview, and `check_layout.py` to validate.

5. **Score with the comeback rubric**: After building, score every dimension
   0-5. Minimum pass: 40/45 (no reference) or 44/50 (with reference). No
   dimension below 4.

6. **Iterate before delivering**: Do not ship the first export. Iterate the
   weakest 2-4 slides. Prefer bold rebuilds over cosmetic fixes.

7. **Use subagents for bounded tasks**: For source extraction, reference critique,
   QA scoring, or appendix work, use subagents with `subagent-instructions.md`.
   The main agent owns story, visual system, and final integration.

### Requirements

- Python 3.9+
- python-pptx
- Pillow

### Scripts

| Script | Purpose |
|--------|---------|
| `build_deck.py` | Assemble slide modules into PPTX |
| `render_slides.py` | Render PPTX to PNG previews |
| `check_layout.py` | Layout quality checker |
| `contact_sheet.py` | Generate thumbnail contact sheet |
| `cleanup.py` | Clean workspace, keep PPTX only |
| `inspect_template.py` | Extract template metadata from PPTX |
| `prepare_starter_deck.py` | Clone selected template slides into starter deck |
| `imagegen_prompt.py` | Write imagegen prompt files (no API calls) |
| `create_reference_slide.py` | Single reference slide prompt generation |
| `create_reference_slides.py` | Batch reference slide prompt generation |
| `render_lucide_icon.py` | Render Lucide icons to PNG/SVG |
| `check_icon_manifest.py` | Validate icon manifest JSON |
| `run_prompt_battle.py` | Matrix battle harness for batch testing |

### License

Distilled from OpenAI Codex Presentations plugin (MIT). Adapted for Claude Code
with python-pptx.
