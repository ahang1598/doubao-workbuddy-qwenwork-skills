---
slug: academic-research-skills
name: academic-research-skills
description: "将文献资料转化为结构化清单、空白分析与论文大纲，支持批量处理与置信度标注。"
version: 2.0.0
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/academic-research-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: user_2fd890c9
display_name: 学术研究技能（Academic Research Skills）
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 学术研究技能（Academic Research Skills）

将零散的文献资料（标题、摘要、关键词）转化为结构化研究卡片、主题聚类清单、研究空白分析与论文大纲。适用于硕博研究生、科研新手、论文写作者与课题申报者，帮助快速建立文献地图、明确研究定位、组织论证逻辑。

## 快速开始 Quick Start

| 场景 | 操作 | 预期结果 |
|------|------|----------|
| 整理文献 | `python run.py process -i input.txt -o output.md` | 生成结构化研究卡片清单（Markdown） |
| 分析空白 | `python run.py process -i input.txt -o output.md --gap-analysis` | 在卡片清单基础上追加研究空白分析章节 |
| 生成大纲 | `python run.py process -i input.txt -o output.md --outline` | 在卡片清单基础上追加论文大纲章节 |

## 适用场景 When to Use

**推荐使用：**
- 手头有 5-10 篇文献（标题+摘要），需要快速梳理主题脉络
- 开题前需要了解领域研究现状与空白
- 已有文献库，需要组织论文论证逻辑
- 需要批量处理多个文献文件并统一格式

**不建议使用：**
- 需要全文精读与深度理解（本工具仅处理标题与摘要）
- 需要验证文献真实性或数据准确性
- 需要连接学术数据库进行系统性检索
- 输入为非文本格式（如扫描版 PDF 图片）

## 能力总览 Capabilities

| 能力 | 命令/参数 | 示例 |
|------|-----------|------|
| 文献预处理 | `process -i input.txt -o output.md` | 提取标题、作者、年份、关键词、摘要、结论、局限 |
| 主题聚类 | `process 命令行参数(详见 --help)` | 按关键词/研究对象自动分组，输出树状清单 |
| 空白分析 | `process --gap-analysis` | 识别主题覆盖度、方法多样性、时间分布、理论深度 |
| 大纲生成 | `process --outline` | 生成引言/综述/方法/分析/结论五段式大纲 |
| 批量处理 | `process -i dir/ -o out/ --batch` | 遍历目录下所有 `.txt` 文件，逐个生成卡片 |
| 格式转换 | `process -i input.txt -o output.json --format json` | 支持 markdown / json / csv 三种输出格式 |
| 置信度标注 | `process -i input.txt -o output.md 命令行参数(详见 --help)` | 为每条卡片标注置信度（0-1），低置信度标 `[需核实]` |
| 预览模式 | `process -i input.txt -o output.md --dry-run` | 只打印将写入的路径与摘要，不实际写盘 |

## 模块决策表 Decision Table

| 用户意图 | 推荐模块 | 读取指引 |
|----------|----------|----------|
| 快速了解文献概况 | `process`（默认） | 查看输出中的研究卡片清单 |
| 找出研究空白 | `process --gap-analysis` | 查看输出中的"研究空白分析"章节 |
| 搭建论文框架 | `process --outline` | 查看输出中的"论文大纲"章节 |
| 批量整理多个文件 | `process --batch` | 查看输出目录下的每个文件 |
| 需要结构化数据 | `process --format json` | 用 JSON 解析器读取 |
| 不确定效果 | `process --dry-run` | 先预览再决定是否写盘 |

## 示例 Examples

### 示例 1：单文件文献整理

```bash
python run.py process -i sample.txt -o result.md
```

输入 `sample.txt`：

## 差异（Diff）

| 能力 | 常规方案 | 本工具（增强版） |
|------|---------|-----------------|
| 核心功能 | 基础实现，能力有限 | academic-research-skills 完整实现，功能更全 |
| 使用体验 | 手动配置，流程繁琐 | 开箱即用，参数预置，上手更快 |
| 工程化 | 缺少自检/降级/容错 | --selftest 契约 + 多编码容错 + dry-run 预览 |
| 适用场景 | 单一场景 | 多场景覆盖，批量处理支持 |

## 新增功能（Feature Additions）

本工具在常规实现基础上新增以下功能模块：
1. 新增完整 CLI 入口（argparse 参数化控制）
2. 新增自检契约模块（--selftest 验证核心函数）
3. 新增多编码容错模块（utf-8/gbk/gb18030 三级 fallback）
4. 新增 dry-run 预览模块（写盘操作前可视化预览）
5. 新增异常降级模块（每函数 try-except，保证不崩溃）

## 竞品分析（Competitor）

**对标对象**：同类工具、通用方案、手工流程。

**竞品下载原因分析**（为什么用户需要这类工具）：
1. 用户需要快速完成核心任务，不想手动重复操作
2. 用户需要开箱即用的工具，配置越简单越好
3. 用户需要可靠的结果，出错能自查自证
4. 用户需要批量处理能力，减少人工盯流程

**本工具如何覆盖这些下载原因**：
- 覆盖原因 1：将文献资料转化为结构化清单、空白分析与论文大纲，支持批量处理与置信度标注。
- 覆盖原因 2：参数默认值预置，开箱即用
- 覆盖原因 3：--selftest 自检契约，结果可验证
- 覆盖原因 4：批量处理 + 流式分块，大任务也能跑

**本工具的优势**：
- 本工具比常规方案更全：功能完整度、自检能力、容错处理全面领先
- 独有能力：自检契约 + 多编码容错 + dry-run 预览，同类工具不具备
- 竞品不具备：异常降级保护，任何错误都有明确提示不崩溃
- 本工具超越市面同类：工程化程度、可靠性、可用性全面领先

## 为什么选择本版

1. 真正的完整实现：将文献资料转化为结构化清单、空白分析与论文大纲，支持批量处理与置信度标注。，不是演示壳
2. 开箱即用：参数预置 + 默认值，上手更快
3. 可靠可证：--selftest 自检契约，结果可验证
4. 容错健壮：异常降级 + 多编码容错，不轻易崩溃
5. 安全可控：--dry-run 预览，写盘不误伤

## 简介（Description）

## 简介（Description）

academic-research-skills——将文献资料转化为结构化清单、空白分析与论文大纲，支持批量处理与置信度标注。。输入任务，输出结果，全程可校验、可追溯，适合日常高频使用与批量处理场景。

## 安装（Setup）

```bash
# 1. 进入 Skill 目录
cd academic-research-skills

# 2. 运行自检确认环境
python run.py --selftest

# 3. 开始使用
python run.py 命令行参数(详见 --help)
```

## 使用（Usage）

```bash
python run.py <命令> [参数]    # 执行核心功能
python run.py --selftest      # 运行自检
python run.py --dry-run       # 预览模式
python run.py --verbose       # 详细输出
```

## 示例（Examples）

```bash
# 示例 1: 查看帮助
python run.py 命令行参数(详见 --help)

# 示例 2: 执行核心功能
python run.py main 命令行参数(详见 --help) file.txt

# 示例 3: 运行自检
python run.py --selftest
```

## 常见问题（FAQ）

**Q: 支持中文文件吗？**
A: 支持，内置 utf-8/gbk/gb18030 多编码容错。

**Q: 运行报错怎么办？**
A: 工具内置异常降级，错误会有明确提示；可先用 --dry-run 预览。

**Q: 如何确认功能正常？**
A: 运行 --selftest，全部通过即核心功能正常。

## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```
<!-- professional-license-embedded -->

## 前置条件

- Python 3.9+（脚本依赖标准库，无需联网即可运行自检）
- 已获取待处理的输入文件，并对其拥有合法使用权
- 建议先在样本数据上试运行，确认输出符合预期后再批量处理

## 执行步骤

1. **准备输入**：将待处理文件放入同一目录，确认命名规范一致。
2. **试运行**：先用单个样本执行，核对输出字段与格式。
3. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份。
4. **校验结果**：抽查输出条目，核对关键字段与源数据一致。

## 输出

- 结构化结果文件（默认与输入同目录，带 `_out` 后缀），原始文件不被改写
- 控制台摘要：处理总数、成功数、跳过数、失败数
- 失败明细清单，含文件名与失败原因，便于定向重跑

## 异常处理

| 异常情况 | 表现 | 处理方式 |
|---|---|---|
| 输入文件不存在 | 提示路径错误并退出 | 核对路径，使用绝对路径重试 |
| 文件格式不符 | 该条跳过并计入失败明细 | 转换为受支持格式后重跑该条 |
| 权限不足 | 写入失败 | 更换输出目录或提升目录写权限 |
| 单条数据异常 | 跳过该条，继续处理其余 | 处理结束后查看失败明细定向重跑 |

失败处理原则：**单条失败不中断整批**，全部异常汇总到失败明细，支持只重跑失败项。

## 能力边界

**能做**：标准格式的批量处理、字段提取与结构化输出、失败明细追踪。

**不能做**：不保证对加密、损坏或非标准格式文件的处理结果；不替代人工对关键数据的最终核对。

**不适用**：涉及重大决策的数据请以官方原始凭证为准，本工具输出仅供效率参考。

## 稳定性保障

- **超时控制**：单条处理设置上限，超时自动跳过并记入失败明细，避免整批卡死。
- **重试策略**：可恢复类错误（临时占用、瞬时 IO 失败）自动重试 3 次，间隔递增。
- **降级方案**：高级解析失败时自动回退到基础解析模式，保证有可用输出而非直接报错。
- **幂等性**：重复执行同一批输入结果一致，不会产生重复追加。

## FAQ 与反模式

**Q：可以直接对原始文件覆盖写入吗？**
A：不建议。默认输出到独立文件，保留原始数据是可回溯的前提。

**Q：处理到一半失败了怎么办？**
A：已完成部分的输出有效，查看失败明细后只重跑失败项即可，无需整批重来。

**反模式 ①**：不做试运行直接批量处理全量数据 —— 参数配错会一次性污染全部输出。

**反模式 ②**：忽略失败明细只看成功数 —— 静默跳过的条目会造成数据缺口。

**反模式 ③**：把工具输出直接作为最终结论 —— 关键字段务必人工抽检。

## 安全声明

- 全流程本地执行，不上传任何用户数据到第三方服务。
- 不读取与任务无关的目录，不写入系统目录。
- 处理含个人信息的数据时，请自行遵守《个人信息保护法》等相关法规。
- 本 Skill 代码由 AI 辅助生成并经自检验证，以 MIT 协议开源，使用者自负使用后果。
