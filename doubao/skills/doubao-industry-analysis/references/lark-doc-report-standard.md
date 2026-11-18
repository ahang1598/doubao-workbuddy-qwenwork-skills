# 飞书文档报告标准（Markdown Upload）

本文件控制 Markdown 六批分片、拼接与整篇校验，以及最终导入飞书/Lark 文档时的交付门禁；它不决定分析判断或报告结构。正文在第4步分六批写入，在第6步拼接为 `output/report.md`，再导入为飞书在线文档。

渲染必须服务于 SKILL.md 的质量标准：数据真实可溯源、判断贯穿一条主线、信息详实、克制专业。如果某个 Markdown 写法、表格样式或飞书展示效果让报告显得浅、拥挤、不可溯源或太像模板，简化渲染、保留内容质量。

## 目录

- 文档输出
- 写作与固定分片
- Markdown 写法
- 拼接与定稿
- 校验规则
- 导入与抽查
- 交付门禁

## 文档输出

- 访问可用且场景合适时，**创建一篇飞书/Lark 文档作为最终交付物**。
- 用描述性标题：`{行业}行业深度研究报告` 或 `{行业}行业深度研究——{一句话核心判断}`。
- `output/report.md` 为完整报告与最终上传源文件；`parts/*.md` 为六批写作分片。
- 把文档链接返回给用户；当预期且可用飞书/Lark 交付时，不要只给本地路径。
- 文档里不要提及本 Skill 名称、内部检索流程、拼接脚本实现细节或本地载荷路径。

## 写作与固定分片

- 在本次任务工作目录运行脚本；下列路径相对该目录。脚本在 Skill 目录时可使用其绝对路径调用，无需把产物写入安装目录。
- 按 `report-finalization.md` 的「写作批次」表依次写入 `parts/`。使用表中 01 至 06 的固定文件名，并将本次任务的 `parts/` 目录仅用于这六个 Markdown 分片。

## Markdown 写法

- 用标准 Markdown 作为唯一写作源。
- 标题层级固定：
  - `#` 主标题
  - `##` 核心观点、板块一至五、风险提示、结语、参考文献
  - `###` 各板块小节与 `回扣主线`
- 执行摘要的核心判断与每章 `回扣主线` 用引用块表达，例如：

```markdown
> **核心判断：** ...
> **关键风险：** ...
> **验证信号：** ...
```

- 使用可稳定导入的 Markdown 原生语法。
- 不使用 html 标签、内嵌 xml、自定义颜色、合并单元格或依赖飞书专属块级语法的写法。

## 拼接与定稿

- 确认六个分片均已写入后，用脚本按文件名顺序拼接为 `output/report.md`，同时执行引用重排。

```bash
python3 scripts/assemble_report.py
```

- 合并时保持章节顺序、补足空行，避免标题、表格、引用块粘连；整篇主标题、参考文献与免责声明各保留一次，五大板块各有 `回扣主线` 小节。

## 校验规则

### 分片校验（按需）

- 写作时保持以下要求；发现问题再做分片定位，不另起一轮重复检查：
  - 本片内容论证完整、信息充分、与主线一致。
  - 标题层级正确，没有跳级标题。
  - 该片的 `回扣主线` 小节按章节需要保留，整篇完整性统一核对。
- 推荐命令：

```bash
python3 scripts/validate_report.py --stage part --file parts/02-industry-definition-scale.md
```

### 阶段校验（按需）

- 需要定位问题时，可对 `parts/` 下已写入的 Markdown 分片做阶段校验：
  - 现有分片非空，无禁用标记。
  - 不上传飞书。
- 推荐命令：

```bash
python3 scripts/validate_report.py --stage stage
```

### 整篇校验

- 整篇完成后，统一做一次整篇校验；合并主文件与定稿清单的同类检查项，建议使用 `scripts/validate_report.py`。修复后仅复核变化处，不重启全文研究。
- 内容检查见 `report-finalization.md` 的「交付前自检清单」。
- 推荐命令：

```bash
python3 scripts/validate_report.py --stage final --file output/report.md
```

## 导入与抽查

- 本地整篇校验通过后，再导入 `output/report.md` 生成飞书/Lark 文档。
- 使用 Drive 导入能力把 Markdown 转为在线文档，不走逐块更新。
- 推荐命令：

```bash
lark-cli drive +import --as user --file output/report.md --type docx --name "{行业}行业深度研究报告"
```

- 如果导入返回异步 ticket，继续查询：

```bash
lark-cli drive +task_result --scenario import --ticket <TICKET>
```

- 可使用 `scripts/upload_report.py` 封装导入与 ticket 查询。上传前可先 dry-run：

```bash
python3 scripts/upload_report.py --file output/report.md --title "测试行业深度研究报告" --dry-run
```

- 上传脚本默认单次命令超时60秒、总期限180秒；超时或失败后返回已有 Markdown 与限制说明，不循环上传或重做研究。
- 上传后做一次交付抽查，重点看：
  - 标题层级与目录导航是否正常。
  - 版式和正文内容是否正确渲染。
  - 抽样确认引用标注、文献链接及引用块正确渲染。
  - 分片拼接处是否出现空行丢失、表格断裂、标题粘连。
- 若上传后渲染异常，优先修正 Markdown 源文件并重新定稿上传，不在飞书端手工补丁式修文。

## 交付门禁

交付前确认：

- 六个固定分片已按顺序拼接，完整 `output/report.md` 内容非空。
- `output/report.md` 已通过整篇校验。
- 飞书文档链接已可用，上传后抽查通过。

> 若上传失败或渲染异常：在对话中给出完整 Markdown 报告内容并说明限制，不要只给一个失败的链接。
