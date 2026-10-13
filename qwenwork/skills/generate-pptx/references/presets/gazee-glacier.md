# Gazee Glacier

默认视觉预设，适用于企业汇报、科技商业方案、管理层演示。

## Visual identity

- 背景：`#F4F9FF -> #E6F0FA` 的浅色冰川渐变
- 主文本：`#0A1931`
- 辅助文本：`#4A6B99`
- 主蓝：`#0068B7`, `#2F75E0`
- 高光：`#00E5FF`, `#40C4FF`
- 卡片底色：`#FFFFFF` 或 `#F8FBFF`

## Layout rules

- 使用 16:9 画布，`viewBox="0 0 1280 720"`
- 拒绝大段文字平铺，优先拆成卡片、时间轴、矩阵、漏斗、进度条、对比图
- 底部保留一条稳重的深蓝色压舱底座，增强汇报感
- 图标只使用纯 SVG 基本图形或路径，不使用 emoji
- 需要图片时，用虚线框或清晰占位符标注

## PPT compatibility rules

- 根元素必须包含 `xmlns="http://www.w3.org/2000/svg"`
- 严禁使用 `<filter>`，包括阴影和模糊滤镜
- 阴影改用偏移的半透明底图模拟
- 发光改用多层半透明图形叠加
- 不输出 HTML、`<script>`、`<style>` 或其他非 SVG 标签

## Output contract

只输出 JSON 数组：

```json
[
  {
    "title": "幻灯片标题",
    "svg": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 1280 720\">...</svg>"
  }
]
```
