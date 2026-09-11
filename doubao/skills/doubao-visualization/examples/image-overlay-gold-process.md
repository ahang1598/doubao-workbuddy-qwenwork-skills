# Gold process —— 阶段一的产物（解题 + 规划，纯 0~999 相对坐标）

这是一道机箱风道题（"前面板无开孔，怎么规划风道"）的 process 范例。注意：

- 它**只活在你的思考里**，是后续内嵌进可视化的数据载荷，**不会**作为文字出现在回复里。
- 坐标全是 **0~999 相对值**，凭视觉判断"在画面约百分之几处"得到，**没有任何像素/宽高**。
- 不限步数，这几条证据最终**合并进同一张图**（见 `gold-reply.md`），不是每条一张。
- 每条 step 只有 `type`（标注类型）+ `coords`；每个 coord 只有 `kind` / 坐标 / `label`——**没有 color**：颜色由阶段三可视化代码自己决定，解题旁白写在回复正文里。
- 这题一次用到了 **4 种标注类型**：框出进风区（bbox_zoom）、画主气流路径（path_grow）、指 CPU→后风扇的排风方向（node_walk）、点出各出风位（count_pop）。类型按"这条证据本质是什么"来选，不硬凑也不漏。

```json
{
  "steps": [
    {
      "type": "bbox_zoom",
      "coords": [
        {"kind": "bbox", "xyxy": [100, 740, 760, 960], "label": "底部进风区：电源仓上方开孔，冷空气主要入口"}
      ]
    },
    {
      "type": "path_grow",
      "coords": [
        {"kind": "point", "x": 400, "y": 940, "label": "底部进风"},
        {"kind": "point", "x": 400, "y": 840, "label": "·"},
        {"kind": "point", "x": 360, "y": 720, "label": "·"},
        {"kind": "point", "x": 340, "y": 600, "label": "·"},
        {"kind": "point", "x": 370, "y": 450, "label": "·"},
        {"kind": "point", "x": 380, "y": 300, "label": "·"},
        {"kind": "point", "x": 380, "y": 160, "label": "·"},
        {"kind": "point", "x": 380, "y": 80,  "label": "顶部出风"}
      ]
    },
    {
      "type": "node_walk",
      "coords": [
        {"kind": "point", "x": 500, "y": 400, "label": "CPU散热器后部"},
        {"kind": "point", "x": 870, "y": 400, "label": "后部风扇"}
      ]
    },
    {
      "type": "count_pop",
      "coords": [
        {"kind": "point", "x": 870, "y": 400, "label": "后部出风：1把风扇向外排风"},
        {"kind": "point", "x": 280, "y": 70,  "label": "顶部出风位①：靠前风扇位"},
        {"kind": "point", "x": 560, "y": 70,  "label": "顶部出风位②：靠后风扇位"}
      ]
    }
  ],
  "final_answer": "前面板无开孔，走「底部进风 + 顶部/后部出风」的微负压风道……（面向用户的完整答案，写在 gold-reply.md 正文里、可视化之前）"
}
```

要点回顾：

- `bbox` 紧贴真正承载判断的进风区，不是松垮框住整张图。
- `path_grow` 用一串有序 `point` 描出气流走线（底部→显卡→CPU→顶部），中间过路点 `label` 用 `·` 占位、只在起终点写字。
- `node_walk` **恰 2 个有序 point**（A=CPU 散热器后部 / B=后部风扇），渲染成一条 A→B 带箭头的有向线，表达排风方向。
- `count_pop` 点出并列的出风位，`label` 写"是什么/干什么"而非只标物体名。
- `label` 全是面向用户的措辞，没有 `x=` / 坐标 / `bbox` 字样。
