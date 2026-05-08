# template-and-edit

当用户提供已有 deck/模板时使用。视为幻灯片库和可编辑起点，而非主题参考。

## 模板契约

默认模式是 **template-starter adaptation**：读取每张源幻灯片，为每张输出幻灯片选择源幻灯片作为起点，复制那些幻灯片，然后在原位编辑复制后的元素。

不要创建只借用配色、字体或氛围的新布局。保留复制幻灯片的母版家具、装饰、占位框、间距韵律、图表框架、页码标记、排版语调和组件几何——除非用户明确要求重设计。

## 源文件检查

检查源 PPTX 后创建：

- `template-audit.txt`：源系统、可复用的幻灯片类型、弱项、不复制的内容、品牌/素材、插入契约
- `template-frame-map.json`：每张输出幻灯片对应的源幻灯片清单
- `deviation-log.txt`：每次意图偏离的理由和影响范围

`template-frame-map.json` 格式：

```json
{
  "outputSlides": [
    {
      "outputSlide": 1,
      "sourceSlide": 3,
      "narrativeRole": "开篇论点",
      "editTargets": []
    }
  ],
  "omittedSourceSlides": [
    {"sourceSlide": 4, "reason": "不需要此类附录"}
  ]
}
```

每张输出幻灯片必须有 `sourceSlide`。源幻灯片可复用多次。

## QA 阻断缺陷

- 输出幻灯片无 `sourceSlide` 映射
- 从模板主题重建而非从源幻灯片复制
- 缺失源幻灯片的装饰/母版家具
- 空白的图像井
- 标题/正文/页脚碰撞
- 字体替换导致严重不一致
- 未经请求的新配色/字体/表面语言
