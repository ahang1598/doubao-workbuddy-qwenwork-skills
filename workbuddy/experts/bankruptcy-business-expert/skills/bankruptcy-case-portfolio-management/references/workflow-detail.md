# 工作流程

> bankruptcy-case-portfolio-management 技能的 7 Phase 详细步骤

---

## Phase 1：意图识别与模式判定

### 目标

识别用户意图，判定操作模式（INIT/UPDATE/PORTFOLIO/DEADLINE/PROGRESS/DUTY_SUMMARY）。

### 步骤

1. **关键词匹配**：
   - INIT：初始化/新建/创建破产案件
   - UPDATE：补充/更新/追加材料
   - PORTFOLIO：台账/清单/有哪些案件
   - DEADLINE：期限/看板/截止日期
   - PROGRESS：进度/进展/待办
   - DUTY_SUMMARY：履职汇总/履职报告/统计

2. **案件存在性检测**：
   - 扫描 `workspace_root` 下已有案件目录
   - 匹配 `debtor_name` 或 `case_id`
   - 无匹配 → INIT；有匹配 → UPDATE

3. **模式确认**：
   - 单案操作 → 对应模式
   - 多案操作 → PORTFOLIO/DEADLINE/PROGRESS/DUTY_SUMMARY

### 输出

- 操作模式
- 目标案件（单案时）
- 筛选条件（多案时）

---

## Phase 2：输入解析与校验

### 目标

解析输入参数，校验必填字段。

### 步骤

1. **参数提取**：
   - 自然语言 → 提取 debtor_name/procedure_type/source_paths 等
   - 参数化 → 直接使用

2. **必填校验**：
   - debtor_name 非空
   - procedure_type 在枚举范围
   - source_paths 路径存在（INIT/UPDATE 时）

3. **推荐参数补全**：
   - 尝试从材料中提取 case_number/court_name
   - 提示用户补充 claim_deadline/first_creditor_meeting

### 输出

- 校验通过的参数对象
- 缺失参数提示（如有）

---

## Phase 3：操作计划生成与确认

### 目标

生成文件系统操作计划，展示给用户确认。

### 步骤

1. **计划生成**：
   - INIT：列出将创建的目录结构、将生成的制品
   - UPDATE：列出将复制的文件、将更新的字段
   - PORTFOLIO/DEADLINE/PROGRESS/DUTY_SUMMARY：列出将扫描的案件、将生成的制品

2. **计划展示**：
   ```
   【操作计划】
   模式：INIT
   目标：BANK-2026-001_XX房产
   将创建：
   - 目录：01-接管材料/02-债权申报/...（共14个）
   - 文件：case-meta.yaml
   将复制：
   - D:\破产案卷\XX房产\ → 01-接管材料/（156个文件）
   是否确认执行？
   ```

3. **用户确认**：
   - 确认 → 进入 Phase 4
   - 修改 → 返回 Phase 2 调整参数
   - 取消 → 终止

### 输出

- 用户确认的操作计划

---

## Phase 4：文件系统操作执行

### 目标

按确认后的计划执行文件系统操作。

### 步骤

1. **INIT 模式**：
   - 创建案件目录结构（按程序类型模板）
   - 复制 source_paths 文件到对应目录
   - 生成 case-meta.yaml

2. **UPDATE 模式**：
   - 检测案件目录是否存在
   - 复制新文件到对应目录
   - 更新 case-meta.yaml（阶段/期限/更新时间）

3. **多案模式**：
   - 扫描 workspace_root 下所有案件目录
   - 读取各案件 case-meta.yaml

### 输出

- 文件系统操作结果
- 生成的/更新的文件清单

---

## Phase 5：制品生成与写入

### 目标

生成 YAML/Markdown 制品，写入对应目录。

### 步骤

1. **YAML 制品**：
   - case-meta.yaml（INIT/UPDATE 时）

2. **Markdown 制品**：
   - portfolio-index.md（PORTFOLIO 时）
   - deadline-dashboard.md（DEADLINE 时）
   - progress-tracker.md（PROGRESS 时）
   - duty-summary.md（DUTY_SUMMARY 时）

3. **模板渲染**：
   - 加载 templates/ 下对应模板
   - 填充实际数据
   - 写入目标路径

### 输出

- 生成的制品文件清单

---

## Phase 6：索引台账与看板更新

### 目标

更新多案件索引台账和跨案期限看板。

### 步骤

1. **INIT/UPDATE 后自动触发**：
   - 重新扫描所有案件
   - 更新 portfolio-index.md
   - 更新 deadline-dashboard.md
   - 更新 progress-tracker.md

2. **期限预警计算**：
   - 当前日期 vs 各案件期限节点
   - 计算剩余天数
   - 判定预警级别（🔴/🟠/🟡/🟢）

### 输出

- 更新的索引台账
- 更新的期限看板

---

## Phase 7：输出交付与更新日志

### 目标

交付制品清单，写入更新日志。

### 步骤

1. **制品清单汇总**：
   - 列出本次生成的所有制品
   - 标注制品路径和格式

2. **更新日志写入**：
   - 时间戳
   - 操作模式
   - 操作内容摘要
   - 生成的制品清单

3. **用户提示**：
   - 展示制品清单
   - 提示关键期限预警（如有）
   - 提示下一步建议操作

### 输出

- 制品清单
- 更新日志条目

---

## 模式-Phase 映射

| 模式 | 执行 Phase |
|------|-----------|
| INIT | 1→2→3→4→5→6→7 |
| UPDATE | 1→2→3→4→5→6→7 |
| PORTFOLIO | 1→2→3→5→6→7 |
| DEADLINE | 1→2→3→5→6→7 |
| PROGRESS | 1→2→3→5→6→7 |
| DUTY_SUMMARY | 1→2→3→5→7 |

---

## 异常处理

| 异常 | 处理 |
|------|------|
| 路径不存在 | 阻断，提示用户检查路径 |
| 权限不足 | 阻断，提示用户检查权限 |
| 案件ID冲突 | 提示用户确认是否覆盖或新建 |
| 日期格式错误 | 警告，尝试自动转换或提示用户修正 |
| 模板文件缺失 | 降级为默认模板，提示用户 |
