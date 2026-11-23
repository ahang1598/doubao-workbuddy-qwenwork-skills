# 互动教学图专家 · Teachable Figures Expert

WorkBuddy 单专家包装：[ywEdAi/teachable-figures](https://github.com/ywEdAi/teachable-figures)（demo: https://ywedai.github.io/teachable-figures/）。

## 做什么

把一个知识点做成 **predict → try → explain** 的可操作互动教学图（离线 HTML）：齿轮传动、Transformer 数据流、圆锥截面、火箭剖切、贝叶斯基率、四季等。

## 许可与署名

| 部分 | 许可 |
|------|------|
| 代码（skill / 示例 HTML/CSS/JS） | MIT © ywEdAi |
| 书面内容与 skill 文案 | CC BY 4.0 © ywEdAi — 可商用，须署「Teachable Figures by ywEdAi」 |
| `assets/anatomy`、`assets/iso-figure` | MIT（见各自 LICENSE） |

**免责**：教学简化模型，非工程仿真，非临床指导。

## 包内 / 包外

- **含**：`skills/teachable-figures/`（SKILL、references、kits、templates、示例 `gear-ratio.html` + `transformer-flow.html`）
- **不含**：`examples/human-anatomy.html`、`assets/hra/`（HuBMAP）、`reviews/`、`tests/`、`node_modules`、Playwright 浏览器
- 可选本机校验见 `SETUP.md`（Node≥20 + Playwright，**不进运行依赖**）

## 版本

`1.0.0` — 新建单专家；不并入 isometric-anatomy / teardown / archify / 开物。
