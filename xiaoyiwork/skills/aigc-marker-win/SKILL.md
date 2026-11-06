---
name: aigc-marker-win
description: 为 Windows 小艺 Work 中已存在的 OOXML 文档与模板、UOF、PDF、OFD、Markdown、XMind、POSM/POSF、HTML、图片、音频和视频文件添加 AIGC 显式标识与隐式元数据。其他生成型 Skill 要求添加 AIGC 标识，或用户要求“添加 AI 生成标识”“添加 AIGC 标签”时使用。
---

# AIGC Marker for 小艺 Work

版本：1.2.1。文本元数据依据 TC260-PG-20258A（V1.0-202508）；条款、格式限制和只读校验见 [references/text-guide.md](references/text-guide.md)。

原地修改目标文件，为其添加 AIGC 标识。不要复制文件到 Skill 目录，不要在任务执行期间安装依赖。

## 支持格式

| 类型 | 扩展名 | 默认显式标识 |
| --- | --- | --- |
| Word 文档／模板 | `.docx`、`.dotx` | 文档末尾“内容由AI生成” |
| PDF | `.pdf` | 每页底部“内容由AI生成” |
| Excel 文档／模板 | `.xlsx`、`.xltx` | 每个工作表末行，并添加打印页脚 |
| PowerPoint 文档／模板 | `.pptx`、`.potx` | 首张非隐藏幻灯片右下角 |
| UOF 文本／模板 | `.uot`、`.uott` | 文档末尾“内容由AI生成” |
| UOF 表格／模板 | `.uos`、`.uost` | 每个工作表末行 |
| UOF 演示／模板 | `.uop`、`.uopt` | 首张非隐藏幻灯片的文字框 |
| OFD | `.ofd` | 每页底部中文水印 |
| XMind | `.xmind` | 每个画布根主题下增加“内容由AI生成”子主题 |
| ProcessOn 导图／流程图 | `.posm`、`.posf` | 各画布原生水印；POSM 根主题下增加提示子主题，POSF 原内容下方增加文本框 |
| Markdown | `.md` | 文末文字，同时写入 YAML 元数据 |
| HTML | `.html`、`.htm` | 页面底部固定标识 |
| 图片 | `.jpg`、`.jpeg`、`.png`、`.webp`、`.heic`、`.heif` | 右下角水印 |
| 音频 | `.wav`、`.mp3`、`.ogg`、`.flac`、`.m4a` | 末尾追加 AI 摩斯码节奏 |
| 视频 | `.mp4`、`.flv`、`.mkv`、`.avi` | 全程右下角水印 |

文本类格式的具体容器、元数据位置和兼容范围见 [references/text-formats.md](references/text-formats.md)。Office 模板保留原模板类型；UOF 支持旧版 XML 兼容标识，以及具有既有元素结构的 2009/2021 ZIP，XMind 支持 XML 与 JSON 包。

传入 `--skip-visible` 可只写入隐式元数据；HTML/HTM 写入 `<meta name="AIGC" content="JSON">` 本地互操作扩展，该扩展不代表第三方平台支持 HTML 隐式标识检测。文本类格式先仅写隐式标识后再次运行默认命令，会补充显式标识；重复运行不会叠加已有水印。

## 执行流程

1. 将目标文件解析为绝对路径，确认文件已经生成并完成内容校验。
2. 优先使用小艺 Work 注入的 `CLAW_PYTHON_EXE`；仅在未注入时回退到系统 Python。
3. 运行入口脚本。路径必须单独作为参数传入，不要拼进 Python 源码。
4. 文本格式先在临时副本写入，再回读校验存储位置、类型与七个 AIGC 字段，通过后才替换原文件；只有脚本退出码为 0 且输出 `AIGC_MARKER_OK` 才算本地标记成功，不代表第三方检测已通过。
5. 作为其他 Skill 的后处理时，成功后由调用方继续交付；用户直接要求标记文件时，调用 `send_file_to_user(abs_file_path_list=["<绝对路径>"])`。

```bash
set -e

PYTHON_CMD=""
if [ -n "${CLAW_PYTHON_EXE:-}" ] && "$CLAW_PYTHON_EXE" -c "import sys" 2>/dev/null; then
  PYTHON_CMD="$CLAW_PYTHON_EXE"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
else
  echo "AIGC_MARKER_FAILED: python_not_found"
  exit 1
fi

"$PYTHON_CMD" "{baseDir}/scripts/main.py" "<绝对文件路径>"
```

只添加隐式标识：

```bash
"$PYTHON_CMD" "{baseDir}/scripts/main.py" "<绝对文件路径>" --skip-visible
```

## 双标识交付与第三方验收

- 用户要求显式和隐式标识时，必须对支持可见标识的最终文件运行默认标记命令，禁止使用 `--skip-visible` 替代双标识；POSM/POSF 默认添加原生画布水印与文本提示，未知画布结构停止并保留原文件；不能只在聊天回复中附上“内容由AI生成”。本技能处理已存在的文件，不会自动拦截所有其他工具的文件生成与交付。
- 新标识按七个字符串字段生成：Label、ContentProducer、ProduceID、ReservedCode1、ContentPropagator、PropagateID、ReservedCode2；Label 必须为标准枚举值，非空字段与字段类型必须正确。两个预留字段允许为空；已有合法来源保留、缺失预留字段补齐；合法来源冲突时停止并保留原文件。
- https://gcmark.com/web/index.html#/mark/check/text 的检测范围和显式、隐式两项结论，以该平台当时的逐文件实际结果为准。不得将“不支持”当作“合规”或承诺所有格式都能通过该站双项检测。
- 网站实测需要登录及逐文件上传；未经实际检测，不得将本地校验结果描述为网站合规结果。使用人工构造且不含私人/业务信息的样例验证，保留文件哈希和每项结果；未验证项必须明确标为待验证。
- 历史版本的网站范围、样例生成与验收说明见 [references/gcmark-validation.md](references/gcmark-validation.md)。

## Windows 运行约定

- Python 依赖声明在根目录 `requirements.txt`，由小艺 Work 后台统一安装；禁止执行 `pip install`。
- 入口按目标文件扩展名加载对应处理器及依赖；某一格式的依赖缺失不会阻断其他格式。例如处理 PDF 时不会导入或要求 `python-docx`。
- PDF、OFD 和媒体可见水印需要中文字体；测试或自定义安装可用 `CLAW_AIGC_FONT_PATH` 指定已有字体文件。字体从 `C:\Windows\Fonts` 和 `%LOCALAPPDATA%\Microsoft\Windows\Fonts` 查找，优先使用客户端安装的 `HarmonyOS_Sans_SC.ttf`。
- 音视频使用小艺 Work 通过 `CLAW_FFMPEG_EXE` / `CLAW_FFPROBE_EXE` 注入的工具，或 PATH 中的 `ffmpeg` / `ffprobe`；Skill 不再安装或携带 ffmpeg。
- 所有临时文件使用系统临时目录或目标文件同目录，不使用 `~/.openclaw` 等云沙箱路径。
- 文件会被原地修改。脚本采用临时文件加原子替换，失败时退出码非 0，禁止继续交付未标记文件。

## 结果判断

- `AIGC_MARKER_OK: <path>`：成功或文件已有完整标识。
- `AIGC_MARKER_FAILED: dependency_not_ready: ...`：等待小艺 Work 后台依赖安装，或在 Skill 页面重试依赖安装。
- `AIGC_MARKER_FAILED: ffmpeg_not_found: ...`：音视频处理依赖未就绪。
- 其他 `AIGC_MARKER_FAILED`：保留原文件，向用户说明错误，不得谎报成功。


## 版本与只读校验

`python "{baseDir}/scripts/main.py" --version` 显示实际运行的技能版本。

`python "{baseDir}/scripts/main.py" "<绝对文件路径>" --verify` 只读校验指南所列的 18 种格式，不会添加标识。成功输出 `AIGC_METADATA_VERIFIED`。旧 UOF1 单 XML 返回 3 并标明不在指南 ZIP 存储范围。该校验不覆盖可见标识和第三方网站验收。

对本指南的隐式标识任务可用 `--skip-visible`；默认命令为 POSM/POSF 同时写入显式和隐式标识。详细要求见 [references/text-guide.md](references/text-guide.md)。

POSM/POSF 识别的原生 JSON 画布、容器限制与脚本验证见 [references/processon-visible.md](references/processon-visible.md)。
