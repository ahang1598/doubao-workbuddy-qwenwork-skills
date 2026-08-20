---
name: artifact-preview
description: >-
  Render workspace artifacts (pdf/pptx/docx/xlsx/html/png/jpg/txt/zip) into text
  + page screenshots + thumbnail + multi-page collages, saved under
  ./.preview/{hash}/. Use Read on the resulting jpg/png files to visually
  inspect your own deliverables before delivering them; it catches what a
  structural checker cannot — text truncation, colour clashes, clipped chart
  titles, layout drift, blank slides, CJK rendered as boxes. Triggered by:
  "看看产物长什么样", "视觉自检", "preview pptx", "render artifact",
  "screenshot pdf", "渲染产物", "我的报告画出来好看吗", "图表是否完整".
license: Proprietary — internal use only.
compatibility: >-
  Linux, macOS or Windows. Needs Python 3.10+ and Pillow; PyMuPDF for pdf,
  python-pptx for pptx text, python-docx for docx, openpyxl for xlsx.
  Screenshots of pptx need a LibreOffice install; screenshots of html need a
  Chromium-family browser (on Windows the preinstalled Edge is enough).
  Missing pieces degrade to text with a warning, never a crash. On Windows
  invoke the entry point as bin/preview.cmd (or `python bin/preview`): the
  extension-less POSIX script cannot be executed directly there.
metadata:
  version: "2.1"
  hub: artifact-preview
---

# Artifact Preview

把产物渲染成文本加截图，交付前用 `Read` 打开图片肉眼检查。

它和 `verifier-hub` 是一对：verifier 回答「文件结构和数值对不对」，
artifact-preview 回答「文件看起来对不对」。

## 什么时候用

在 `verifier rubric check-file-format` 通过之后、正式交付之前，
对可渲染的产物跑一次。典型 PPT 或 PDF 大约 5 秒，并且按内容 hash 缓存，
同一个没改过的文件重复调用几乎不花时间。

| 类型 | 会得到什么 | 视觉检查价值 |
|------|-----------|------------|
| `.pptx` / `.ppt` | 文本 + 每页截图 + 拼图 | 高：版式、配色、图表是否放得下、文字是否溢出 |
| `.pdf`           | 文本 + 每页截图 + 拼图 | 高：版式、图片位置、中文是否正常显示 |
| `.html`          | 原文 + 视口截图 | 高：实际渲染效果、样式是否失效、资源是否缺失 |
| `.docx`          | 文本（含表格），**不出图** | 低：只能看内容，看不到排版 |
| `.xlsx`          | 各 sheet 的单元格文本，**不出图** | 低：只能看内容 |
| `.png` / `.jpg` 等 | 缩略图 | 低：本来就是图，只是缩了一份 |
| `.txt` / `.md` / `.json` / `.csv` | 原文 | 无：直接 Read 原文件更省事 |
| `.zip`           | 条目清单文本 | 无：看结构用 `verifier archive zip-list` |

docx 和 xlsx 按设计不出图。把它们渲染成图片需要走一遍 LibreOffice 转换，
收益不足以抵掉那几秒，所以只给文本。需要看 docx 的实际排版就先自己转成 PDF 再 preview。

## CLI 形态

优先用工作区内的相对路径调用：

```
./skills/artifact-preview/bin/preview
```

Windows 上换成同目录的 `.cmd` 包装，或者直接把无扩展名的脚本交给 Python：

```powershell
.\skills\artifact-preview\bin\preview.cmd render .\report.pptx
python .\skills\artifact-preview\bin\preview render .\report.pptx
```

下文所有示例都写成 POSIX 形式，Windows 上按上面这两种写法替换即可。

## 输出协议

每个子命令在 stdout 输出**一个** JSON 对象，参数写错时也一样：

```json
{"ok": true,  "tool": "render", "result": {...}}
{"ok": false, "tool": "render", "error": {"code": "...", "msg": "..."}}
```

错误码：`FILE_NOT_FOUND`、`NOT_A_FILE`、`BAD_EXT`、`NOT_FOUND`（缓存里没有这一项）、
`DEP_MISSING`、`BAD_ARGS`、`RENDER_FAILED`、`INTERNAL`。

注意区分两件事：**缺依赖导致某种格式出不了图，不算错误**。
这种情况仍然是 `ok: true`，图片列表为空，原因写在 `result.warnings` 里。
所以拿到结果先看 `warnings`，再决定要不要读图。

## 用法

### 1. 渲染

```bash
./skills/artifact-preview/bin/preview render ./report.pptx
```

`result` 里的路径字段都是绝对路径，可以直接交给 `Read`：

```json
{
  "ok": true,
  "tool": "render",
  "result": {
    "output_dir": "/home/user/.../workspace/.preview/abc123def456",
    "manifest": "/.../.preview/abc123def456/manifest.json",
    "kind": "pptx",
    "page_count": 12,
    "rendered_page_count": 12,
    "collage_count": 2,
    "extracted_text_chars": 4521,
    "text": "/.../.preview/abc123def456/text.md",
    "thumbnail": "/.../.preview/abc123def456/thumb.jpg",
    "collages": ["/.../c1.jpg", "/.../c2.jpg"],
    "pages": ["/.../pages/p001.png", "..."],
    "warnings": []
  }
}
```

### 2. 按需读

为了少花 token，按这个顺序读：

1. 先 `Read` **thumbnail**，快速看一眼整体。
2. 需要核对内容再 `Read` **text**。
3. 缩略图里看出某处可疑，再 `Read` 对应的 **collage**。
4. 拼图分辨率不够时，才 `Read` 单页 **pages**。

```
Read ./.preview/abc123def456/thumb.jpg     ← 最便宜，先看这个
Read ./.preview/abc123def456/text.md
Read ./.preview/abc123def456/c1.jpg        ← 一张图里含多页
```

`Read` 会把图片直接作为图像内容返回给你，你看到的是画面，不是路径。

只要生成了拼图，就一定覆盖全部已渲染页面，不会漏掉最后一页。
只有一页的产物不出拼图，缩略图就是那一页。
万一真有页面没进拼图，`warnings` 里会点名是哪几页并给出单页文件路径。

### 3. 发现问题就改

改完源文件再跑一次 `preview render <file>`。输出目录名由文件内容算出来，
所以改过的文件自动落到新目录，旧的预览保留。清理用 `preview clean <hash>`
或 `preview clean --all`。

## 子命令

```bash
preview render <file>              # 渲染并输出 JSON
preview render <file> --text-only  # 只出文本，跳过渲染
preview render <file> --no-collage --no-thumbnail
preview render <file> --max-pages 5
preview render <file> --page-range "1-3,7,10-12"
preview render <file> --force      # 忽略缓存，重新渲染
preview render <file> --soffice <path>    # 手动指定 LibreOffice，用于 pptx 截图
preview render <file> --chromium <path>   # 手动指定浏览器，用于 html 截图

preview info <file|hash|dir>       # 输出完整 manifest
preview list                       # 列出所有缓存的预览
preview clean <hash>               # 删掉一项缓存
preview clean --all                # 删掉全部缓存
```

`--output-root` 对 `render` / `info` / `list` / `clean` 都可用，
也可以用环境变量 `ARTIFACT_PREVIEW_HOME` 统一指定缓存根目录。

`--text-only` 只是跳过这一次的渲染工作，**不会删掉**之前完整渲染留下的图片。
遇到这种情况 `warnings` 里会说明图片是上一次渲染留下的。

## 视觉自检清单

`Read` 缩略图和拼图时，重点看这些 verifier 查不出来的问题：

| 问题 | 看什么 |
|------|--------|
| 文字溢出 | 文字跑出文本框，或者被截断留下省略号 |
| 标题被裁 | 页面或图表标题上下缺一块，或者移出画布 |
| 配色冲突 | 大面积靛蓝紫色调（除非任务明确要求） |
| 版式错位 | 列没对齐、莫名的空档、页边距不一致 |
| 图表异常 | 空的柱子、缺图例、坐标轴标签错 |
| 空白页 | 内容之间夹着空页，通常是套模板留下的 |
| 语言渲染 | 中文显示成方块，说明字体回退失败 |

## 和 verifier-hub 配合

交付前的典型顺序：

```bash
# 结构与格式（verifier）
./skills/verifier-hub/bin/verifier rubric check-file-format ./report.pptx --expected-ext .pptx
./skills/verifier-hub/bin/verifier pptx list-slides ./report.pptx

# 视觉检查（本 skill）
./skills/artifact-preview/bin/preview render ./report.pptx
# 然后 Read thumb.jpg，必要时再 Read 拼图
```

写交付说明时，结构类事实引用 verifier（「12 页，每张图表都有图例」），
视觉类判断只写你真的 Read 过图之后看到的（「版式匀称，配色统一」）。

## 输出目录结构

```
.preview/<source-hash>/
├── manifest.json       先读这个，知道有哪些东西可用
├── text.md             抽出的文本（pdf / pptx 按页分段）
├── thumb.jpg           单张总览图，最长边不超过 768px
├── pages/              每页整分辨率图片
│   ├── p001.png
│   └── ...
└── collages/           多页拼合图
    ├── c1.jpg
    ├── c2.jpg
    └── ...
```

目录名是文件内容的 SHA-256 前缀。内容完全相同的两个文件共用同一份缓存。

## 限制与行为

- `--max-pages` 默认 **12**，长文档要更多页就显式指定。
- 大于 100 MB 的文件用前缀 hash 做缓存键，仍然通过文件大小复核，不会误命中。
- `pptx` 截图需要 LibreOffice。没有就只出文本，`pages` 为空并记一条 warning，
  `ok` 仍然是 `true`，不会让调用方失败。
- `html` 截图需要 Chromium 系浏览器。找不到就只出 `text.md` 并记 warning。
  找到了但浏览器没能真正加载文档时会报错，不会拿一张无关的截图冒充成功。
- `xlsx` / `docx` 按设计不出图，只输出竖线分隔的文本。
- 缺 Python 依赖（PyMuPDF、python-pptx、python-docx、openpyxl、Pillow）时，
  对应格式的文本或图片为空并记 warning。要恢复某种格式就装它的依赖：

  ```bash
  pip install --target "$HOME/.artifact-preview-pylibs" pymupdf python-pptx python-docx openpyxl Pillow
  export PYTHONPATH="$HOME/.artifact-preview-pylibs:$PYTHONPATH"
  ```

  Windows / PowerShell 上没有 `$HOME` 和 `export`，改用：

  ```powershell
  python -m pip install --user pymupdf python-pptx python-docx openpyxl Pillow
  ```

  沙箱里**不要**用裸 `pip install`：venv 的 site-packages 不可写，
  user site 又没有 sys.path 优先级，两种默认路径都会失败。
  `DEP_MISSING` 的 `msg` 里已经按当前平台把命令拼好了。

  系统程序装法：`apt-get install -y libreoffice chromium-browser`；
  Windows 上是 `winget install --id TheDocumentFoundation.LibreOffice -e`，
  HTML 截图直接用系统自带的 Edge，不用另装。
  已经装了但不在 PATH 上（macOS 和 Windows 的安装器都不加 PATH），
  用 `--soffice` / `--chromium` 指定路径，或者设
  `ARTIFACT_PREVIEW_SOFFICE` / `ARTIFACT_PREVIEW_CHROMIUM`。

## 缓存根目录

默认写到当前目录下的 `./.preview/<hash>/`。
用环境变量 `ARTIFACT_PREVIEW_HOME` 或 `--output-root` 可以改。
当前目录不可写时退到 `$HOME/.preview/`。
