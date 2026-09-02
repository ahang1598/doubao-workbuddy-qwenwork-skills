---
name: patent-expert-orchestrator
description: |
  CNIPA 发明专利申报全流程 SOP（团队行动手册）。主理人调度 13 位专家完成从体检、检索、引证、验真、盲区审计、权项优化、交底书架构、合规闸门、附图、格式终检到打包的全流程作业基准。
  触发词：CNIPA 申报流程、专利申报 SOP、全流程调度、申报门禁、Gate B/Gate C、来源影响判定。
---

# CNIPA 发明专利申报全流程 SOP（团队行动手册）

> 本手册由原独立技能 `patent-cnipa-filing` 合并入本专家团（v2.0.3），作为主理人调度全流程的作业基准。
> 覆盖：Step 1.0 体检 → 1.7 质量闸门（Gate B）→ 2.1 附图 → 2.2 格式终检 → 2.3 打包（Gate C）。

## 参考资料

执行本 SOP 前必读：@references/cnipa-filing-sop.md —— 完整的步骤分解、门禁规则、附图工具链坑、说明书官方格式铁规与主流表达结构。

## 本 Skill 的角色

这是**主理人调度专用 SOP 参考 skill**，不是由某个团员独立执行的子能力。主理人 `patent-expert-orchestrator` 在编排全流程时加载本 skill 获取：
- 全流程 11 步（Step 1.0 ~ 2.3）的步骤分解与团队成员分工映射
- ★ 来源影响判定门禁（出正式说明书前必过）的 5 步铁规
- 附图工具链实战坑（Graphviz splines、清华镜像、样式铁规、图数由说明书决定）
- 说明书官方格式铁规（章节/段号/背景↔发明内容分工/三段式/实施方式框架）

## 全流程 SOP 概览（对应团队成员分工）

```
Step 1.0 体检        → 材料成熟度、附图占位、主体信息、引用溯源（主理人）
Step 1.1 检索        → 对比专利/论文真实性核验（查新师 patent-prior-art-searcher / 文献师 patent-literature-search）
Step 1.2 引证据      → 删虚构、更正硬伤、重建 GB/T7714 引用清单（引证师 patent-citation-matcher）
Step 1.3 验真明      → 五步幻觉核验：作者/状态/DOI 等（幻觉哨兵 hallucination-guard）
Step 1.4 焦窗明      → Johari 四象限 + 溯源表 + 隐藏区排查（盲区审计师 johari-window-auditor）
★ 来源影响判定门禁（人工主导，见 §2）
Step 1.5 范方圆      → 权项优化：独权+从属，结构核验（权项师 patent-claim-optimizer）
Step 1.6 文述理      → 整合修订三件套：纠错+统一符号+理论标注（架构师 patent-disclosure-architect）
Step 1.7 法正清 Gate B → 质量闸门：7维评分+四级闸门（合规官 patent-compliance-checker）
Step 2.1 图致准      → 附图生成（绘图师 patent-figure-drawer，Graphviz 工具链见 §3）
Step 2.2 格式终检    → 11 项核验（见 packager/references/patent_filing_checklist.md）
Step 2.3 包综汇 Gate C → 跨文档一致性闸门 + 打包清单（打包师 patent-packager）
```

## ★ 来源影响判定门禁（出正式说明书前必过）

顺序不可颠倒：
1. **人工溯源**所有来源（由用户核验真实性，AI 不代验）
2. **人工确认**信息准确
3. 对每条来源判「是否影响专利成果」+ **过程 + 原因** → 三结果：加固 / 无价值（删）/ 颠覆（重判可行性）
4. 确认专利**加固**后 → 出正式成果 → 形成**说明书**
5. **说明书 = 所有上报资料唯一基础**（权项/摘要/附图/请求书全部派生）

铁规：溯源只服务加固/颠覆；不相干不要、AI 候选「无价值」一律删；门禁未关闭前说明书一律视为草稿，AI 仅作智囊团候选（标盲区 + 过程 + 原因），不得代断。

## 调用方式

本 skill 由主理人在编排全流程时自动加载，无需用户手动触发。完整 SOP 细节、附图工具链坑、说明书格式铁规见 @references/cnipa-filing-sop.md。
