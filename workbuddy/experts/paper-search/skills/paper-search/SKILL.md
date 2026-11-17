---
name: paper-search
description: 学术论文检索技能（OpenAlex 250M+ 文献，免费无 API Key）。按关键词检索论文，或按 DOI / OpenAlex ID 查单篇详情（作者、被引、摘要、开放获取链接）；OpenAlex 429 限流时自动降级 Semantic Scholar。当用户需要查文献、找论文、学术检索、按 DOI 查文章、查被引次数、找开放获取 PDF、写研究/报告要科学依据时使用。Search for academic papers by keyword, or look up a specific paper by DOI or OpenAlex ID. Powered by OpenAlex (250M+ works, free, no API key).
version: 2.0.0
---

# Paper Search — 学术论文检索

> v2.0.0 专家级（2026-09-07）：九要素结构化升级——补定位/触发/分步工作流/输出规范/边界/依赖/范例；search.sh / paper.sh 命令与参数、双后端降级（OpenAlex→Semantic Scholar）全部原样保留。

## 〇、专家级路由（v2.0.0）

**专家定位**：免费学术论文检索专家。OpenAlex 2.5 亿文献打底，429 自动降级 Semantic Scholar。

**五维评估**：
- 适用场景：综述前收集文献；回答要科学依据；按 DOI 核对单篇；找开放获取 PDF
- 能力边界：只给元数据与 OA 链接，不做全文下载解析、非学术检索
- 依赖资产：scripts/search.sh + scripts/paper.sh + curl/jq；无需 API Key
- 交付质量：条目含作者/年份/被引/DOI；引用前经 paper.sh 核对
- 性能表现：单次检索默认 10 条、上限 200；限流自动兜底

**四级响应（L1-L4）**：
- L1 按 DOI/ID 查单篇 → paper.sh 直接取详情
- L2 关键词检索 → search.sh 出清单（作者/年份/被引）
- L3 综述选题检索 → 多轮检索 + related_works 链式扩展
- L4 研究依据包 → 检索 + 逐篇核对 + 文献清单 + OA 链接

**黄金窗口**：每次 10-20 条、按被引排序取前 10；query 限定 3-6 个实词
**专家件索引**：scripts/search.sh（关键词检索）、scripts/paper.sh（单篇详情）

## 一、定位声明

本技能用两个 bash 脚本查学术论文：`search.sh` 按关键词检索（OpenAlex 主、
Semantic Scholar 兜底），`paper.sh` 按 DOI 或 OpenAlex ID 取单篇完整信息
（作者/摘要/概念/开放获取 PDF/相关文献）。给智能体用于"找文献、查论文、要科学依据"
类任务。免费、无需 API Key、无需注册。脚本位于技能目录 `scripts/` 下。

## 二、触发条件

- 触发词：查文献 / 找论文 / 学术检索 / 论文搜索 / 按 DOI 查 / 看某篇论文被引 /
  找开放获取 PDF / scientific backing / paper search / literature。
- 触发场景：综述写作前收集文献；回答需要引用出处的问题；核对某篇论文详情；
  探索引用图谱（related works 链式查询）。
- 不触发：网页普通搜索（用 agent-reach/web 搜索）；本地 PDF 解析（用 textin-xparse）。

## 三、脚本定位

脚本与 SKILL.md 同目录：技能注册路径 `/root/.skills/paper-search/scripts/`，
插件/镜像安装时以 SKILL.md 所在目录的 `scripts/` 为准。调用前先解析出
`<scripts-dir>`，不要硬编码绝对路径。

## 四、分步工作流

1. **输入判定**：用户要"搜一批论文" → 走 search.sh；用户给了 DOI/OpenAlex ID
   或要单篇完整信息 → 走 paper.sh。
2. **关键词检索**（search.sh）：
   ```
   <scripts-dir>/search.sh "your search query" [limit] [sort] [page]
   ```
   - `limit`：每页条数（默认 10，最大 200）
   - `sort`：`relevance`（默认）/ `cites` / `date`
   - `page`：页码（默认 1）
   - 后端：OpenAlex 主通道；返回含 "Rate limit exceeded"（429）时自动降级
     Semantic Scholar 并在 stderr 提示 `[backend] ... 已降级 Semantic Scholar`。
3. **单篇详情**（paper.sh）：
   ```
   <scripts-dir>/paper.sh <DOI_URL or OpenAlex_ID>
   ```
   - 接受完整 DOI URL（如 `https://doi.org/10.3390/brainsci8020020`）
   - 或 OpenAlex ID（如 `W2789811475`），也接受 `https://openalex.org/...` 链接
   - 返回：作者、摘要、concepts、开放获取 PDF 链接、related works。
4. **补全摘要**：search 结果显示 "Abstract: N/A" 时，用 paper.sh 取全文摘要。
5. **链式探索**：paper.sh 返回的 `related_works` ID 可再喂回 paper.sh 沿引用图谱扩展。
6. **检查点**：结果非空才算成功；网络/限流失败如实告知，必要时稍后重试一次。

## 五、输出规范

- 检索结果按脚本原始输出整理，保留：序号、标题、被引数、年份、作者（前几位）、DOI/链接。
- 引用论文时给出（作者, 年份, 期刊/来源）格式；不编造不存在的论文或元数据。
- 需要交付文献清单时用 markdown 列表 + 链接；注明后端（OpenAlex / Semantic Scholar）。

## 六、边界与反模式

- 不适用：全文下载与解析（本技能只给元数据与开放获取链接，全文解析用 textin-xparse）；
  非学术检索（新闻/网页用 agent-reach）。
- 禁止：把检索结果当成已核实事实直接引用——引用前用 paper.sh 核对作者与年份。
- 常见错误：query 太宽泛（"bilingualism brain" 命中差）；限流失败后反复重试同一命令
  （脚本已自动降级 Semantic Scholar，重试交给脚本内部逻辑或稍后）；把 related_works
  ID 当论文标题引用。

## 七、依赖说明与降级

- 工具依赖：`curl` + `jq`（脚本内部使用；缺失时先安装）。
- 数据依赖：OpenAlex API（免费、无需 key，250M+ works）；Semantic Scholar API 为限流兜底。
- 降级链：OpenAlex 429 → 脚本自动降级 Semantic Scholar（relevance 固定；date 映射
  year:desc，cites 映射 citationCount:desc）→ 仍失败则等 25s 后重试一次 → 如实报告失败。
- 无需 API Key；离线不可用时如实说明网络原因。

## 八、实战范例

> 示意；具体结果【待核：以实际 API 返回为准】。

- 输入："帮我找找双语认知优势与执行功能关系的最新论文，要引用靠前的。"
- 处理：`search.sh "bilingual cognitive advantages executive function" 10 cites`
  按被引排序取前 10 → 挑 3-5 篇最相关的 → 逐篇 `paper.sh W…` 取完整摘要与开放获取 PDF 链接。
- 输出：文献清单（作者, 年份, 标题, 被引, 链接）+ 简短推荐理由。
  实际命中的论文列表以命令输出为准【待核：xx】。

## 九、版本记录

- v2.0.0（2026-09-07）：九要素结构化升级，补定位/触发/工作流/输出规范/边界/依赖/范例；
  search.sh（OpenAlex→Semantic Scholar 自动降级）与 paper.sh 命令、参数、排序语义全部原样保留。
