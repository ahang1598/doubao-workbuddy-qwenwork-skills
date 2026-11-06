---
name: xiaoyi-report-win
description: "从多源信息生成带引用的专业分析报告。当用户要求研究、调研、调查、分析某个主题，或需要搜索资料、收集信息时使用。支持学术研究、市场调研、竞品分析、技术调研、深度研究。相关请求示例：'帮我调研XXX'、'帮我分析XXX'、'写一份关于XXX的深度研究报告'、'深度分析XXX'。任务完成后主动将生成的HTML报告文件通过channel发送给用户查看。"
version: 0.2.1
---

# 小艺报告专家

基于多源搜索生成深度研究报告。

---

## 核心原则

- **深度优于广度**：对关键来源进行深度阅读
- **证据驱动**：每个核心论断必须有可靠来源支撑
- **多角度分析**：从技术、商业、社会等多维度审视
- **诚实透明**：遇到知识空白时明确说明

---

## ⛔ 执行进度追踪

**执行要求：** 在回复中持续展示当前进度，每完成一步更新状态：

```
✅ 1. 需求澄清
✅ 2. 研究规划
⏳ 3. 信息搜索与提取 ← 当前阶段
- [ ] 4. 交叉验证
- [ ] 5. 深度分析
- [ ] 6. 撰写报告
- [ ] 7. 质量审查
- [ ] 8. HTML转换与交付
```

---

## 步骤概览

### 步骤 1-2：准备阶段

1. **需求澄清**：确认研究目标（学习/决策/撰写/商业分析）和约束条件
2. **研究规划**：根据问题难度，拆分3-8个研究维度进行关键词搜索，注意单轮关键词长度控制在15个字符以内

详见 `references/workflow.md`

### 步骤 3：信息搜索与提取

为每个研究维度单独执行信息检索和整理。

**搜索脚本：**

```bash
node /home/sandbox/.openclaw/workspace/skills/xiaoyi-web-search/scripts/search.js "[关键词]" -n 8
```

详见 `references/workflow.md`

---

## ⛔ Gate 1：进入报告撰写前

**必须输出此验证表才能继续撰写报告：**

| 关键数据  | 来源1   | 来源2   | 验证状态         |
| ----- | ----- | ----- | ------------ |
| [数据项] | [URL] | [URL] | ✅一致/⚠️差异/❌矛盾 |

⚠️ 验证不通过？返回步骤4补充交叉验证。

---

### 步骤 4-5：分析阶段

4. **交叉验证**：对关键数据进行多源验证
5. **深度分析**：趋势分析、对比分析、风险评估

详见 `references/workflow.md` 和 `references/validation.md`

---

### 步骤 6-7：报告阶段

6. **撰写报告**：按模板生成报告
7. **质量审查**：检查数据准确性、时效性、完整性

**报告模板：** 见 `references/report-template.md`

**验证规则：** 见 `references/validation.md`

---

## ⛔ Gate 2：HTML转换（强制执行）

> ⚠️ **路径硬性约束（最常见报错源头）**：`md2html.js` 内置安全校验，**只允许处理**当前任务工作空间 `reports/` 子目录下的 `.md` 文件。报告必须写在 `reports/[slug]/` 下（如 `reports/climate-rice-impact/report.md`）。
> - 若把报告放在 `report\`、`output\` 或其他非 `reports/` 目录，会报错：`输入文件必须位于允许目录内`（退出码 1）。
> - **确保输入和输出都在 `reports/` 内**，不要直接指定工作空间根目录或自定义目录。

**创建报告目录（Windows 环境推荐用 PowerShell，规避 Git Bash 的 MSYS 噪音）：**

```powershell
# PowerShell 方式（推荐）
New-Item -ItemType Directory -Path "reports/[slug]" -Force
```

```bash
# 或 Git Bash 方式（可能打印 MSYS 噪音，但无功能影响）
mkdir -p "reports/[slug]"
```

> 💡 **关于 Git Bash 的 stderr 噪音**：执行 `mkdir -p` 等命令时可能打印 `/etc/msystem: line 26: /etc/msystem.d/MSYS: No such file or directory`，这是 MSYS 兼容层初始化脚本缺失导致的**非阻塞错误**，退出码仍为 0、目录已创建，**可忽略**。
> 如需完全规避，直接改用它种方式：PowerShell `New-Item` 或 `bash` 的 `mkdir -p` 均可，Windows 下推荐 PowerShell。

**HTML 转换（必须使用此脚本，禁止其他方式）：**

```bash
node "{baseDir}/scripts/md2html.js" "reports/[slug]/report.md"
```

不要 `cd` 到 Skill 目录；每次 `exec` 的初始 `$PWD` 是当前任务工作空间。脚本只允许读写当前工作空间的 `reports/` 子目录。

**禁止行为：**

- ❌ 使用pandoc或其他工具
- ❌ 自己生成HTML代码
- ❌ 使用其他转换脚本

---

### 步骤 8：交付

1. 确认 `report.html` 已生成
2. 取得 `"$REPORT_DIR/report.html"` 的绝对路径
3. 调用 `send_file_to_user` 发送该绝对路径（**传入单个字符串**，见下方参数说明）
4. 工具成功返回后再通知用户，不得只输出本地路径

> ⚠️ **`send_file_to_user` 参数类型**：参数名 `abs_file_path_list` 虽带 `_list`，但不同环境的 schema 校验存在差异——有的要求**字符串（单一路径）**，有的接受数组。**保守做法：始终传字符串**（单一路径时传 `".../report.html"`，多个文件时分别调用或按当前环境 schema 支持的数组格式传入）。若传 Python 列表触发 `Input should be a valid string` 校验错误，改传字符串即可。

---

## 详细指引

按需阅读以下文件：

| 文件                              | 内容                 |
| ------------------------------- | ------------------ |
| `references/workflow.md`        | 每个步骤的详细操作说明        |
| `references/report-template.md` | 完整报告结构模板           |
| `references/validation.md`      | 验证规则、来源可信度分级、置信度评级 |

---

## 附录 A：常见报错与规避（Windows / Git Bash）

> 以下是在 Windows 桌面环境（Git Bash + MSYS 兼容层）执行本技能时较常见的报错，均不影响最终交付，但按下面方式可规避或正确处置。

| 现象 | 根因 | 正确处置 |
|------|------|----------|
| `mkdir -p` 打印 `/etc/msystem: line 26: ... No such file or directory`，但退出码 0 | Git Bash 基于 MSYS，`/etc/msystem` 初始化脚本在本环境缺失，属非阻塞噪音 | 忽略即可；目录已创建。想完全规避，改用 PowerShell `New-Item -ItemType Directory` |
| `md2html.js` 报 `输入文件必须位于允许目录内`，退出码 1 | 报告放在了 `reports/` 之外（如 `report\`、工作空间根目录） | 把 `.md` 放到 `reports/[slug]/` 下再转换。脚本硬性安全校验，只认 `reports/` 子目录 |
| bash 里执行 `copy` 报 `command not found`（退出码 127） | `copy` 是 Windows cmd 内置命令，非 Git Bash 可执行命令 | Git Bash 用 `cp`；或改用 PowerShell `Copy-Item` |
| `send_file_to_user` 报 `abs_file_path_list Input should be a valid string` | 该环境的 schema 要求传字符串而非 Python 列表 | 传**单个字符串**绝对路径；需要发多个文件时，按当前环境 schema 决定字符串或数组 |

**原则：** Windows 下凡需创建目录、复制文件，优先用 PowerShell cmdlet（`New-Item`、`Copy-Item`），可同时规避 MSYS 噪音与 cmd/bash 命令差异；路径一律走 `reports/` 子目录。
