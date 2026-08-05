# 措辞分寸校准

综述的可信度取决于每句话的措辞强度是否和证据强度匹配。说得太满被专业读者一眼看出；说得太软让综述失去判断力。

## 核心原则：claim strength ≤ evidence strength

## Hedge Ladder

### 强（多项独立研究一致支持、meta-analysis、大规模验证）

| 英文 | 中文 |
|---|---|
| demonstrate, establish, show, confirm | 表明、证实、确立 |
| consistently, robustly | 一致地、稳健地 |
| 多项独立研究证实、已被反复验证 | |

### 中（2-3 项研究支持，条件有限）

| 英文 | 中文 |
|---|---|
| suggest, indicate, support the view that | 提示、说明、支持……的看法 |
| be consistent with, point to | 与……一致、指向 |
| 现有证据表明、多数研究指向 | |

### 弱（仅 1-2 项研究，或仅有机制论证）

| 英文 | 中文 |
|---|---|
| may, might, could | 可能、或许 |
| appears to, seems likely | 似乎、看来 |
| 初步证据提示、有待进一步验证 | |

### 无证据

| 英文 | 中文 |
|---|---|
| to our knowledge, no study has examined | 据检索结果，尚无研究考察过 |
| it remains an open question | 仍是一个开放问题 |

## 常见失误

### 说得太满
- ✗ "X proves Y"（prove 几乎只用于数学证明）
- ✗ "This is the best approach"（无限定最高级）
- ✗ "首次提出/唯一的/最优的"（除非有充分核实）
- ✓ 加条件限定："Among methods evaluated on dataset D, this achieves the highest score on metric M"

### 说得太软
- ✗ "It may possibly suggest that there could perhaps be..."（四重 hedge）
- ✓ "The evidence suggests a moderate positive effect"

### 相关写成因果
- ✗ "X causes Y"（除非有因果推断证据）
- ✓ "X is associated with Y" / "X 与 Y 存在相关性"

## 不要为了"专业"堆术语

专业感来自判断的精确和证据的匹配，不来自术语密度。

- ✗ "The paradigmatic shift in the methodological landscape necessitates..."
- ✓ "Methods have changed significantly since 2023, and earlier conclusions may no longer hold."

## 元声明校准

核验类声明（"已核验""准确无误""均真实存在"）本身也是 claim，适用同一原则：**声明强度 ≤ 核验强度**。

- 存在任何"二手核验"或"未核验"字段时，禁用全称量词（"全部""均""确保准确无误"）。
- 诚信声明 / 核验声明不自由撰写，由 citation-guard 的核验台账生成：按"已核验 / 二手核验 / 未核验"三档报数并逐项列出，注明未能访问的数据库与核验执行日期（见 `sub-skills/citation-guard/references/ledger-and-statements.md`）。
- 声明与报告其他部分不得自相矛盾：声称"全部核实"同时在局限性里承认"部分基于推断"，是红线错误。

## 校准的立场

claim ≤ evidence 不等于永远骑墙。当证据权重明显不对称（如 6/8 篇同向、且异向者可被调节变量解释）时，“双方观点并存”本身就是校准错误——它**低报**了证据状态，与夸大同罪。校准的立场 = 方向 + 条件 + 证据计数 + 剩余不确定性，四件套齐全的判断比含糊的中立更诚实。裁决程序（见 `sub-skills/research-synthesis/references/insight-protocol.md`）的三种结局都是校准合法的；缺席判断不是。

