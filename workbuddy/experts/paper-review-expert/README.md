# 论文评审与过稿优化专家（过稿官 / PassGuard）

同时带着**期刊审稿人**与**答辩评委**两顶帽子审论文：七维度百分制评分、退稿风险（红线）排查、按 PRI 优先级排序的修改清单，目标只有一个——**让论文更容易通过**。

## 类型

Agent 型（单个 AI 专家）

## 功能

| 能力 | 说明 |
|------|------|
| 七维度百分制评分 | 选题与创新性 / 结构与逻辑 / 文献与引用规范 / 研究方法与数据统计 / 论证与证据充分性 / 学术表达 / 格式合规与投稿就绪度；三套场景权重（学位论文 / 中文期刊 / 英文期刊），输出等级与通过率区间 |
| 一票否决红线筛查 | 学术不端、伦理缺失、统计或方法致命、形式致命四类；命中即判"不予通过"并给补救路径 |
| 缺陷清单与 PRI 排序 | 8 大类 66 项检查，每条按 S（严重度）× O（普遍程度）× E（暴露度）算 PRI（1–125），分级 P0 必改 / P1 应改 / P2 可优化 / P3 锦上添花 |
| 隐性雷区提示 | 单独挑出"评审人当场未必发现、但一被追问就暴露"的问题 |
| Before → After 改写 | 每条 P0/P1 给可直接替换的段落级文本 + 改动依据 + 副作用提示 |
| 投稿冲刺 | 就绪度检查、三档选刊匹配、Cover Letter、Response to Reviewers 草稿 |
| 答辩预演 | 模拟方法论专家 / 领域专家 / 统计审稿人三类提问 + 应答要点 + 反例预案 |

### 四种工作模式

1. **M1 全篇评审**（默认）——完整评审报告
2. **M2 单章精修**——指定章节的问题与段落级改写
3. **M3 投稿冲刺**——就绪度 + 选刊 + 信件
4. **M4 答辩预演**——三类评审人提问清单与应答脚本

### 配套技能 `paper-review-toolkit`

| 资源 | 用途 |
|------|------|
| `scripts/paper_score.py` | 加权算分、等级、通过率区间、PRI 排序、报告生成、模型自检（`selftest`，24 项） |
| `references/scoring-rubric.md` | 七维度细则、三套权重、分档锚点、评分纪律 |
| `references/defect-checklist.md` | 66 项检查清单、PRI 算法、高频缺陷 PRI 参考表 |
| `references/redlines-and-format.md` | 红线清单、GB/T 7714 / APA / IEEE 要点、查重降重边界、选刊与信件 |
| `references/modes-and-reports.md` | 四模式 SOP、答辩预演脚本、改写规范、复评机制 |
| `templates/review-report.md` | 评审报告骨架 |

## 使用示例

- 把论文发我（全文或某一章都行），我先跑七维度评分与退稿风险排查，给出按优先级排序的必改项。
- 我准备投这本期刊 / 要过这场答辩，帮我做投稿就绪度检查，把必改项和可改项分开列出来。
- 模拟三位评审人审我这篇论文，预测他们会提什么问题，并给出应答要点与反例预案。

## 命令速查

```bash
cd skills/paper-review-toolkit
python3 scripts/paper_score.py weights        # 查看权重与分级
python3 scripts/paper_score.py selftest       # 模型自检
python3 scripts/paper_score.py report --input session.json --out review.md
```

## 边界与合规

- 定位是**评审与优化**，不代写整篇论文、不代拟研究数据。
- 不提供规避查重 / 规避 AI 检测的方法；"降重"仅限合法改写与引用规范化。
- 不编造期刊名称、分区、影响因子与查重阈值，不确定处标注 `[需核实]`。
- 通过率区间为经验估算，不构成任何录用承诺。

## 头像

头像位于 `avatars/expert.png`，已自动生成。如需替换：
- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px，单张不超过 500KB

## 安装

专家包目录：

```
/Users/babywen/.workbuddy/plugins/marketplaces/my-experts/plugins/paper-review-expert/
```

注册命令：

```bash
python3 scripts/register_expert.py <expert-dir>
```

## 打包分享

```bash
python3 scripts/package_expert.py <expert-dir>
```
