# SCI多组学专家（SCI Multi-Omics Expert）

对标 Nature / Cell / Science 顶刊水准的多组学与生物信息学 AI 科研专家：把一个研究主题淬炼成可行、创新、可复现、可投稿的完整研究方案，并用真实计算数据做到发表级。

## 类型

Agent 型（单个 AI 专家），内置 `esc-aging-multiomics` 技能（10 阶段闭环工作流 + 15 条全局要求）。

## 功能

- **Phase 0 主题凝练**：检索顶刊文献、解析 GEO/ENCODE 等高质量公共组学数据、多篇整合，输出"可行性 × 创新性"排序的候选方向与整合数据表。
- **Phase 1 图集先行**：代码前先产出中文、逐图的详细分析大纲（每图含科学论断、A/B/C 子图、统计检验与阈值、CNS 规格、工作量估算），等用户确认后才动手。
- **Phase 2 数据获取**：带大小 / MD5 校验与失败重下的 ENCODE/GEO 下载，产出数据清单。
- **Phase 3–4 多组学流程**：RNA-seq / ChIP-seq / MeDIP / miRNA / scRNA-seq / scATAC-seq / 10x Multiome，纯 Python（不用 R），保存可审计的中间矩阵。
- **Phase 5–6 差异与网络**：跨层共识排序、TF–靶标 / 表观 / miRNA / motif 网络构建，输出跨 ≥2 层收敛的候选机制排序表。
- **Phase 7–8 机制与转化**：数据驱动选定唯一主线机制，对接临床队列与干预靶点。
- **Phase 9 发表产出**：CNS 图规出图（PDF + PNG 双格式）、CNS 图规、结构化学术 Markdown、Word/PPT 导出。

**全局铁律**：先规划后编码、机制数据驱动不预设、按图可复现、真实数据零编造、图表双格式、图内英文、流程图节点标注数据集与方法、PMID 可验证。

## 使用示例

- 「我要研究[主题]，请先做文献与组学数据景观调研，凝练可行且新颖的方向，再给出逐图的中文分析大纲。」
- 「基于已确认的图集大纲，帮我下载并校验所需 GEO/ENCODE 数据，按图复现目录结构逐图分析出图。」
- 「帮我对比体内与体外胚胎干细胞的基因组稳定维持基因表达差异，并挖掘其上下游调控机制。」

## 目录结构

```
sci-multiomics-expert/
├── .codebuddy-plugin/
│   └── plugin.json          # 专家核心配置与市场展示信息
├── agents/
│   └── sci-multiomics-expert.md   # Agent 人设与工作流程
├── skills/
│   └── esc-aging-multiomics/      # 内置技能（SKILL.md + references/ + scripts/）
├── avatars/
│   └── expert.png           # 512×512 头像
└── README.md
```

## 头像

头像已生成在 `avatars/` 目录下。如需替换为自定义头像，要求：
- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB

## 安装

将专家包目录放到专家目录下：

```
C:\Users\DELL\.workbuddy\plugins\marketplaces\my-experts\plugins\sci-multiomics-expert\
```

然后运行注册命令使其可见：

```bash
python3 scripts/register_expert.py <expert-dir>
```

## 打包分享

```bash
python3 scripts/package_expert.py <expert-dir>
```

## 上架与收费

本专家可通过 WorkBuddy 开放平台（open.workbuddy.cn）提交审核并上架专家市场，按 token 消耗获得分成。上架步骤与分成机制见随包交付的《上架与收费指引》。
