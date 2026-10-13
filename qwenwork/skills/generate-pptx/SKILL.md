---
name: generate-pptx
description: 通过多轮沟通收集需求、确认逐页结构、生成每页 SVG 幻灯片并输出 PPTX 文件。适用于用户要求生成 PPT/PPTX、制作演示文稿、把文案或提纲转成幻灯片、先确认页纲再出稿，或需要把模型生成的 SVG 幻灯片打包成可下载 PPTX 的场景。
install_source: official
install_method: download
skill_id: official_7T4xWH8c
enabled_at: 1791893843595
version: 1.0.0
name_zh: 生成 PPTX
---

# Generate PPTX

按“环境准备 -> 需求澄清 -> 页纲确认 -> 逐页 SVG 生成 -> 打包 PPTX”的顺序工作。

## Workflow

### 1. Prepare the Python environment

先检查当前命令是否运行在虚拟环境里：

- 如果当前已经在虚拟环境中，直接复用当前解释器
- 如果当前不在虚拟环境中，在 skill 根目录下创建 `.venv`
- 无论复用哪个解释器，都要确保装有 `python-pptx`

优先运行：

```bash
python skills/generate-pptx/scripts/ensure_skill_env.py
```

后续所有 Python 脚本都通过统一入口执行，不要直接调用底层脚本：

```bash
python skills/generate-pptx/scripts/run_in_skill_env.py skills/generate-pptx/scripts/slides_json_to_pptx.py slides.json -o output.pptx
```

如果安装依赖时遇到网络或权限限制，向用户说明需要允许安装 `python-pptx`。

### 2. Clarify the brief

先通过多轮对话收集以下信息：

- 主题和标题
- 受众和使用场景
- 目标页数，或让你来建议页数
- 已有素材：长文案、提纲、数据、图片占位需求
- 视觉偏好：高管汇报、产品发布、科技感、极简等

如果信息不全，继续追问；如果用户只给了长文案，先把内容压缩成适合演示的叙事结构。

### 3. Propose the slide plan before drawing

在生成 SVG 前，先给出逐页页纲并等待确认。每页至少说明：

- 页标题
- 本页要表达的核心观点
- 采用的版式或图形结构
- 是否需要图片区/数据图/时间轴/对比卡片

如果用户已经明确给出逐页内容，可以跳过这一轮确认。

### 4. Load the visual preset

默认读取 `references/presets/gazee-glacier.md`，按其中的视觉规范和 PPT 兼容约束生成 SVG。

如果用户明确要求其他风格，可以调整配色和排版，但仍必须保留这些底层约束：

- 根元素带 `xmlns="http://www.w3.org/2000/svg"`
- `viewBox="0 0 1280 720"`
- 不使用 `<filter>`
- 不输出 HTML、`<script>` 或 `<style>`

### 5. Generate slide SVGs

按下面的 JSON 数组格式生成结果，只包含数组本身：

```json
[
  {
    "title": "封面",
    "svg": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 1280 720\">...</svg>"
  }
]
```

要求：

- 每页都输出完整 SVG 字符串
- `title` 用于排查和命名，不要省略
- 遇到数字、阶段、对比、流程时，优先转成图形结构，不要堆砌段落
- 需要图片区时，用虚线框或明显占位符表示，不要伪造真实照片

### 6. Build the PPTX

把 JSON 保存为文件后，调用脚本：

```bash
python skills/generate-pptx/scripts/run_in_skill_env.py skills/generate-pptx/scripts/slides_json_to_pptx.py slides.json -o output.pptx
```

若需要同时导出中间 SVG 文件用于排查：

```bash
python skills/generate-pptx/scripts/run_in_skill_env.py skills/generate-pptx/scripts/slides_json_to_pptx.py slides.json -o output.pptx --write-svg-dir exported_svgs
```

也可以直接把已经存在的 SVG 文件打包成 PPTX：

```bash
python skills/generate-pptx/scripts/run_in_skill_env.py skills/generate-pptx/scripts/embed_svg_to_pptx.py slide_001.svg slide_002.svg -o output.pptx
```

### 7. Validate the result

完成后至少检查三件事：

- JSON 能被解析，且每页都有 `title` 和 `svg`
- 脚本成功生成 `.pptx`
- 如果导出了中间 SVG，抽查第一页和最后一页是否满足 1280x720 约束且没有 `<filter>`

## Resources

### `references/presets/gazee-glacier.md`

默认视觉预设。需要生成高管汇报风格、浅色科技风、商业感较强的页面时读取它。

### `scripts/slides_json_to_pptx.py`

把模型生成的 JSON 数组直接转成 PPTX，是最稳定的打包入口。

### `scripts/embed_svg_to_pptx.py`

把现成的 SVG 文件列表嵌入到 PPTX。适合已经手头有 SVG 文件，或需要单独调试嵌入过程时使用。

### `scripts/ensure_skill_env.py`

检查当前是否已经在虚拟环境里；如果没有，就在 skill 目录下创建 `.venv`；然后确保 `python-pptx` 已安装。

### `scripts/run_in_skill_env.py`

统一的 Python 执行入口。先准备可用环境，再用那个解释器执行目标脚本。
