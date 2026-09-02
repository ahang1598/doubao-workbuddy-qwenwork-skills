# 输入规范 — 著作权侵权"实质性相似+接触可能性"分析

> 版本：v3.0.0 | 遵循 base/governance/version-and-quality-governance.md

---

## 一、输入模式

本技能支持两种输入模式，Phase 0 自动识别：

| 模式 | 说明 | 优先级 |
|------|------|--------|
| Mode A: CaseRecord IR | 消费上游 `ip-infringement-clue-miner` 产出的结构化 CaseRecord | 优先 |
| Mode B: 裸输入 | 用户直接提供文字描述或文件，无 CaseRecord | 兜底 |

---

## 二、输入参数

### 2.1 必填参数

| 参数 | 类型 | 说明 | 校验规则 |
|------|------|------|----------|
| `plaintiff_work` | string/file | 原告主张权利的作品（文字描述或原始文件） | 非空；文字描述≥50字或提供文件 |
| `defendant_material` | string/file | 被控侵权素材（文字描述或原始文件） | 非空；文字描述≥50字或提供文件 |

### 2.2 推荐参数

| 参数 | 类型 | 说明 | 缺失影响 |
|------|------|------|----------|
| `contact_evidence` | object | 接触线索（见 §2.3） | 接触可能性评估降级 |
| `work_type` | enum | 作品类型（见 §2.4） | 自动识别，标注假设 |
| `claimed_rights` | array | 涉诉权利项（见 §2.5） | 默认分析复制权，提示用户补充 |
| `originality_description` | string | 原告对独创性元素的主张描述 | 独创性提取依赖自动分析 |

### 2.3 接触线索子参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `plaintiff_publish_date` | date | 原告作品发表时间 |
| `defendant_creation_date` | date | 被告素材创作/发布时间 |
| `distribution_channels` | array | 原告作品传播渠道（平台/展会/出版物等） |
| `industry_relationship` | string | 双方行业交集或合作关系 |
| `cooperation_history` | string | 合作历史（如有） |
| `indirect_contact_chain` | string | 中间环节传播链 |

### 2.4 作品类型枚举

> 依据《著作权法》第3条

| 枚举值 | 说明 | 比对方法论 |
|--------|------|-----------|
| `literary` | 文字作品 | 情节/结构/语言风格/人物设定 |
| `oral` | 口述作品 | 表达内容/表述方式 |
| `musical` | 音乐作品 | 旋律/和声/节奏/曲式结构 |
| `dramatic` | 戏剧作品 | 情节/对话/舞台指示 |
| `quyi` | 曲艺作品 | 唱词/表演设计 |
| `dance` | 舞蹈作品 | 编舞/动作序列 |
| `acrobatic` | 杂技艺术作品 | 动作设计/编排 |
| `art` | 美术作品 | 构图/色彩/线条/造型 |
| `architecture` | 建筑作品 | 空间布局/外观造型 |
| `photographic` | 摄影作品 | 构图/光影/取景/后期 |
| `audiovisual` | 视听作品 | 镜头语言/剪辑节奏/画面构图/音画配合 |
| `graphic` | 图形作品 | 图形设计/比例/标注 |
| `model` | 模型作品 | 造型/比例/结构 |
| `software` | 计算机软件 | 代码结构/算法/界面设计 |
| `compilation` | 汇编作品 | 选材/编排/结构 |

### 2.5 涉诉权利项枚举

> 依据《著作权法》第10条

| 枚举值 | 权利 | 比对重点 |
|--------|------|----------|
| `reproduction` | 复制权（第10条第1款第5项） | 表达的相同/近似复制 |
| `adaptation` | 改编权（第10条第1款第14项） | 改变作品创作出具有独创性的新作品 |
| `film_production` | 摄制权（第10条第1款第13项） | 以摄制视听作品的方法将作品固定在载体上 |
| `integrity` | 保护作品完整权（第10条第1款第4项） | 歪曲/篡改损害作者声誉 |
| `info_network_transmission` | 信息网络传播权（第10条第1款第12项） | 有线/无线方式向公众提供 |
| `distribution` | 发行权（第10条第1款第6项） | 出售/赠与原件或复制件 |
| `exhibition` | 展览权（第10条第1款第8项） | 公开陈列美术/摄影作品原件/复制件 |
| `performance` | 表演权（第10条第1款第9项） | 公开表演作品 |
| `translation` | 翻译权（第10条第1款第15项） | 改变语言文字 |

### 2.6 可选参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `case_name` | string | 案件名称 |
| `analysis_perspective` | enum | 分析视角（plaintiff/defendant/objective） |
| `case_stage` | string | 案件阶段（诉前/一审/二审/再审） |
| `prior_analysis` | string | 已有分析意见 |
| `defense_clues` | object | 被告抗辩线索（见 §2.8） |

### 2.7 作品类型×典型侵权方式映射表

> Phase 1 作品类型分类后，须锁定该类型的典型侵权方式，确定比对重点。

| 作品类型 | 典型侵权方式 | 比对重点 |
|----------|-------------|----------|
| 文字作品（小说/散文） | 情节抄袭/人物设定复制/结构编排模仿 | 情节链映射、人物关系对比、叙事结构对比 |
| 文字作品（代码） | 源码复制/结构抄袭/接口设计模仿 | AFC测试（抽象→过滤→比较）、代码结构对比 |
| 美术作品（平面） | 构图复制/造型抄袭/色彩方案模仿 | 整体观感+关键构成要素对比 |
| 美术作品（珠宝/工业设计） | 造型复制/工艺模仿/装饰元素抄袭 | 造型对比、工艺参数对比、装饰细节对比 |
| 音乐作品 | 旋律复制/和声进行模仿/节奏型抄袭 | 动机(motif)级片段比对、曲式结构对比 |
| 视听作品 | 镜头语言复制/剪辑节奏模仿/画面构图抄袭 | 分镜层面时间轴比对、镜头调度对比 |
| 摄影作品 | 构图复制/光影模仿/取景角度抄袭 | 构图比例对比、光影方案对比、取景角度对比 |
| 软件作品 | 代码复制/界面设计抄袭/算法逻辑模仿 | 代码结构对比、界面元素对比、算法流程对比 |
| 图形作品 | 图形设计复制/比例模仿/标注方式抄袭 | 图形要素对比、比例参数对比、标注规范对比 |
| 汇编作品 | 选材复制/编排结构模仿 | 选材范围对比、编排顺序对比 |

### 2.8 被告抗辩线索子参数

> Phase 7.5 被告抗辩预判的输入线索（可选，缺失时基于比对结果推断）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `defendant_creation_evidence` | string | 被告独立创作证据（创作过程记录/草稿/时间戳等） |
| `defendant_access_impossibility` | string | 被告主张接触不可能的依据（地理隔离/时间不可能等） |
| `prior_art_references` | array | 被告可能引用的在先技术/公有领域素材 |

---

## 三、CaseRecord IR 字段映射

当 Mode A 消费上游 CaseRecord 时，字段映射关系：

| CaseRecord 字段 | 本技能参数 | 说明 |
|-----------------|-----------|------|
| `case.facts.work_description` | `plaintiff_work` | 原告作品描述 |
| `case.facts.infringement_material` | `defendant_material` | 被控侵权素材 |
| `case.facts.contact_info` | `contact_evidence` | 接触线索 |
| `case.clues.copyright_type` | `work_type` | 作品类型线索 |
| `case.clues.claimed_rights` | `claimed_rights` | 涉诉权利项线索 |

---

## 四、输入校验规则

Phase 0 执行以下校验：

| 校验项 | 规则 | 失败处理 |
|--------|------|----------|
| 必填参数存在 | `plaintiff_work` 和 `defendant_material` 均非空 | 🔴阻断，提示用户补充 |
| 描述充分性 | 文字描述≥50字 | ⚠️降级，标注"描述过简" |
| 时间逻辑 | `plaintiff_publish_date` 早于 `defendant_creation_date` | ⚠️标注时间异常 |
| 权利项合法 | `claimed_rights` 中的值在枚举范围内 | 默认分析复制权 |
| 作品类型识别 | 自动识别或用户指定 | 标注识别置信度 |

---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->
