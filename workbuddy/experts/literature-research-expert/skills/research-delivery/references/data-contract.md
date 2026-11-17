# 研究成果数据契约

生成器接收已由专家整理的UTF-8 JSON，不解析PDF、不搜索数据库、不验证DOI是否真实。内容字段为纯文本，输出HTML会转义。完整格式参考../templates/example-research.json及其合成来源demo-sources.md。

| 字段 | 类型 | 要求 |
| --- | --- | --- |
| title topic scope version search_log | 非空文本 | 标题、主题、范围、版本、实际检索或资料来源日志 |
| review_type | 枚举 | narrative、scoping、systematic；输入名称不代表程序验证了综述方法 |
| assumptions | 文本数组 | 可空；假设及待确认条件 |
| papers | 非空对象数组 | 文献P记录，详见下文 |
| methods | 非空对象数组 | 方法M记录，含name、fit、requirements、strengths、limitations、feasibility、recommendation、paper_ids |
| claims | 非空对象数组 | 论断C记录，详见下文 |
| research_questions | 非空对象数组 | R编号、text、inference、method_ids |
| review_sections | 非空对象数组 | title、text、claim_ids，按主题排列 |
| plan_sections | 十个章节对象 | key、title、text、question_ids、method_ids、claim_ids |

P记录字段：id（P1等）、title、authors（非空数组）、year（整数或null）、venue、doi（文本或null）、url（http/https或null）、study_id（相关报告使用相同标识）、verification、verification_note、access、screening、screening_reason、question、source、design、population、sample、measures、analysis、findings、limitations和evidence对象。

verification为crosschecked、user_supplied、unverified或synthetic。access为fulltext、abstract、bibliographic或unavailable。screening为include、exclude或pending。evidence为七个字段（design、population、sample、measures、analysis、findings、limitations）各自对应的非空位置文本。没有资料时明确写“未报告/待全文核实/不适用”和原因，不用空白或0替代。

C记录字段：id、text、kind（empirical、synthesis、proposal）、certainty、limitations、evidence数组。证据项含paper_id、location、relation（supports、contradicts、qualifies）。前两种kind必须有证据，proposal可无。用于综合的证据必须来自include且fulltext/abstract的记录，不能引用排除、待定或仅题录材料。作者输入的证据位置仍须人工回查，程序不能证明准确。

plan_sections的key必须恰好包含background、design、sampling、measurement、analysis、ethics、feasibility、timeline、risks、deliverables。各章节关联相应R编号，可选M/C编号。稳定ID只用P/M/C/R加正整数；同类唯一，引用必须存在。方法比较可引用待定文献以标出未知，但不得借此宣称已取得研究结果。

完整生成命令（在技能目录）：

```text
python scripts/build_research.py --input templates/example-research.json --output research-output
```

目录必须尚不存在。先验证，后临时生成，成功再整体改名；输入失败不会返回伪成品。输出01文献矩阵、02方法比较、03综述草稿、04研究方案、05来源与核查清单的Markdown与HTML，并保留research.json和index.html。Markdown可直接编辑，HTML用于离线搜索、阅读和打印；未提供Office格式生成器。

含synthetic记录的成果始终显示合成演示声明。普通记录仍显示草稿与核验边界，不因结构通过而称已经发表、通过伦理审批或完成真实实验。

只读核验：`python scripts/build_research.py --input research.json --check-only`，不写任何成果。正文引用使用[P1]格式，综述/方案中的P引用必须出现在该节claim_ids对应的证据中；程序不检查自然语言是否歪曲文献，也不能识别所有其他引用格式。所有R问题在design、sampling、measurement、analysis四章都应有对应且与该问题至少一种方法相匹配。

DOI会去doi.org/doi:前缀并转小写再比较；同一标准化DOI的两条include记录会被拒绝，需要人工核对并保留筛选说明，不自动删除。同标题年份的候选与同study_id多报告仅提示。study_groups是输入标识的分组数，不证明各组独立。

新增06证据链与研究对齐.md/html。核查清单展示摘要访问、未核实题录、多报告等提示。scoping/systematic类型会提醒尚未验证综述全流程，不自动颁发方法合规结论。
