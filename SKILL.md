---
name: presentations-cc
description: Build premium, narrative-driven PPTX decks with python-pptx for Claude Code. Distilled from OpenAI Codex Presentations plugin — 8 industry profiles, 9-phase workflow, comeback rubric, anti-pattern guardrails. Use for business presentations, investor decks, product narratives, and any task where "clean" is not enough.
version: 1.0.0
---

# Presentations

构建高质量、可编辑的 PPTX 演示文稿。目标：像优秀编辑、分析师和设计师共同打造的作品，而非"够用就行"的模板。

使用 **python-pptx** 构建（16:9，13.333×7.5 英寸）。每张幻灯片一个独立的 `slides/slide_NN.py` 文件，导出 `build(slide, prs)` 函数。

工作区：`outputs/<task-slug>/`，内含 `slides/` `preview/` `qa/` 及规划文本文件。最终输出为 `<deck-title>.pptx`，不用通用名。

## 轻量 / 完整模式

- **≤5 页简单 deck**（如快速汇报）：跳过 Phase 4-5 的详细规划文件，直接从 claim spine 跳到 build。但仍需过 comeback rubric。
- **≥6 页或客户交付级**：走完整 9 阶段流程。

## North Star

缩略图尺寸下，deck 应展现连贯的视觉系统、独特韵律和证据驱动叙事。可读尺寸下，每页一个**主张**、一个**证明对象**，无填充内容。看起来像通用模板就继续迭代。

## 工作流

### Phase 0 — 锁定任务模式

`create` 从零构建 | `reference-beating` 超越参考 deck | `template-following` 继承模板 | `targeted-edit` 局部修改

区分源 deck（内容来源）和参考 deck（质量标杆）。

### Phase 1 — 路由到 Profile

选择主 profile，读取同级 `profiles/<profile>.md`：

`product-platform` SaaS/产品/平台 | `finance-ir` 财报/投资者 | `gtm-growth` GTM/增长/营销 | `engineering-platform` 技术/AI/基础设施 | `strategy-leadership` 董事会/战略 | `consumer-retail` 消费品/品牌 | `template-and-edit` 模板继承 | `appendix-heavy` 密集附录

多 profile 适用时，选交付风险最高的为主，其余为次要门槛。

### Phase 2 — 源素材读取

- 源 deck：渲染 PNG + 提取文本，区分内容来源/视觉标杆/反模式
- 源数据：提取精确指标和来源日期，写入 `data.json`，绝不编造
- 品牌真实性：logo/吉祥物等身份资产有验证来源就用，没有就省略

创建 `source-notes.txt` + `data.json`。

### Phase 3 — 叙事脊柱（Claim Spine）

**先写故事，后做设计。** 每页非附录幻灯片：

- **kicker**: 1-3 字，如 `增长引擎`
- **主张标题**: 结论，不是主题标签
- **证明对象**: 图表/表格/时间线/示意图
- **支撑说明**: 简洁、事实、来源可查

错误：`收入与利润率趋势`
正确：`增长放缓，但利润引擎持续扩张。`

标题换公司名仍成立 → 继续打磨。证明对象太薄 → 不合格。

创建 `claim-spine.txt`：论点、受众、一句话弧线、每页 claim + 证明对象 + 来源。

### Phase 4 — 设计系统锁定

写代码前创建 `design-system.txt`，定义背景系统、调色板、字体配对、图表/示意图/连接线/容器语法、标题/kicker/footer 语法、允许布局家族、禁止装饰。

商业 deck 偏好：暖纸深墨背景 / 衬线体主张+无衬线体标签 / 细线代替框轮廓 / 开放构图 / 图表直接标注 / 少对象强层级。

### Phase 5 — 联系表规划

`contact-sheet-plan.txt`。10 页至少 5 种宏观布局。硬限制：最多 2 个卡片网格 / 连续 3 页不能同一布局 / 无装饰圆角卡片。

### Phase 6 — 构建幻灯片

`slides/slide_NN.py`，每页一个：

```python
def build(slide, prs):
    """slide: pptx.slide.Slide, prs: pptx.Presentation"""
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor

    # 背景
    bg = slide.background; fill = bg.fill; fill.solid()
    fill.fore_color.rgb = RGBColor(0x1A, 0x1A, 0x2E)

    # kicker — marker + label 共享同一垂直中心线
    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(3), Inches(0.4))
    p = txBox.text_frame.paragraphs[0]
    p.text = "GROWTH ENGINE"; p.font.size = Pt(10)
    p.font.color.rgb = RGBColor(0xE6, 0x00, 0x12)

    # claim title
    # proof object — chart/table/diagram as geometry system
```

图表、示意图、连接线作为几何系统：连接线连续穿过正确标记、标签锚定对应对象、等角色框严格对齐、kicker 的 marker 和 label 垂直居中误差 ≤1px。

### Phase 7 — 渲染预览

```bash
python scripts/build_deck.py --slides-dir $WORKSPACE/slides --out $WORKSPACE/deck.pptx --slide-count <n>
python scripts/render_slides.py --pptx $WORKSPACE/deck.pptx --output-dir $WORKSPACE/preview
python scripts/check_layout.py --pptx $WORKSPACE/deck.pptx --output $WORKSPACE/qa/layout-issues.json
```

脚本路径相对于 SKILL.md 所在目录。逐一检查预览 PNG，修复布局/排版/间距。

### Phase 8 — Comeback Rubric

`qa/comeback-scorecard.txt`，每维度 0-5：

| 维度 | 标准 |
|------|------|
| story | 标题是主张，序列有弧线 |
| specificity | 不能通过名词替换测试 |
| rhythm | 联系表有变化的宏观布局 |
| whitespace | 呼吸自如，不空洞 |
| chart clarity | 图表证明一句话，标签直接 |
| typography | 字体有意为之，非默认 |
| restraint | 无填充框、徽章、装饰杂乱 |
| precision | 指标精确，来源可查 |
| coherence | 一个视觉系统贯穿全 deck |
| reference delta | 明显优于参考（有参考时） |

**最低通过线**：有参考 ≥44/50，无参考 ≥40/45；无维度低于 4；reference delta ≥4（有参考时）。

Profile 门槛是 pass/fail，位于数字 rubric 之上——高分低 profile 仍不合格。

### Phase 9 — 迭代

不要第一次导出就停止。迭代最弱 2-4 页，优先重建弱页而非修修补补。

## 阻断性反模式

修复后才能交付：

- 标题陈述主题而非结论
- 图例可被直接标注替代
- 图表显示数据但不证明标题
- 证明对象太薄无法支撑主张
- 容器比内容更显眼 / 圆角卡片作为默认 / 连续三页同一构图
- 联系表像模板包 / 正文仅为填空间
- 低分辨率 logo、未经证实的指标、模糊来源标签

## 最终交付

1. 确认 PPTX 存在且非空、页数正确
2. 渲染全部为 PNG 并逐一检查
3. 输出文件使用有意义的标题，不用 `output.pptx`、`deck.pptx`
4. 附简短 scorecard 摘要和参考差距说明
