# 示例3：已有案件补充材料（UPDATE 模式）

> 展示已有案件补充材料和更新状态的流程

---

## 场景设定

已有案件 BANK-2026-001（XX房产，重整，债权审查阶段），现需补充新材料并更新阶段。

---

## 用户输入

```
补充XX房产破产案的新材料：D:\新到材料\债权申报表.pdf、银行流水.xlsx。
当前阶段更新为：财产调查。
财产状况报告提交截止日：2026-08-10。
```

---

## Phase 1：意图识别与模式判定

- 识别关键词："补充"、"新材料"、"更新"
- 模式判定：UPDATE
- 检测已有项目：匹配到 BANK-2026-001

---

## Phase 2：输入解析与校验

```json
{
  "case_id_override": "BANK-2026-001",
  "source_paths": ["D:\\新到材料\\债权申报表.pdf", "D:\\新到材料\\银行流水.xlsx"],
  "current_stage": "asset_investigation",
  "duty_report_deadline": "2026-08-10",
  "operation_mode": "UPDATE"
}
```

---

## Phase 3：操作计划生成与确认

```
【操作计划】
模式：UPDATE
目标：BANK-2026-001_XX房产
将复制：
- 债权申报表.pdf → 02-债权申报/申报材料/
- 银行流水.xlsx → 03-财产调查/银行流水/
将更新：
- current_stage: claim_review → asset_investigation
- duty_report_deadline: 2026-08-10
- updated_at: 2026-07-21T11:00:00
是否确认执行？
```

用户确认。

---

## Phase 4：文件系统操作执行

- 复制文件：2个（债权申报表.pdf 2.3MB，银行流水.xlsx 1.1MB）
- 更新 case-meta.yaml

---

## Phase 5：制品生成与写入

更新后的 case-meta.yaml（关键变更）：

```yaml
case_id: "BANK-2026-001"
# ... 其他字段不变 ...
current_stage: "asset_investigation"  # 变更：claim_review → asset_investigation
stage_cn: "财产调查"  # 变更：债权审查 → 财产调查
deadlines:
  claim_deadline: "2026-08-15"
  first_creditor_meeting: "2026-09-01"
  reorganization_plan_deadline: "2026-12-31"
  distribution_plan_announcement: ""
  duty_report_deadline: "2026-08-10"  # 新增
updated_at: "2026-07-21T11:00:00"  # 更新
stage_history:
  - stage: "claim_review"
    entered_at: "2026-07-18T09:00:00"
    exited_at: "2026-07-21T11:00:00"
    trigger: "债权审查完成，转入财产调查"
  - stage: "asset_investigation"
    entered_at: "2026-07-21T11:00:00"
    exited_at: ""
    trigger: ""
duty_nodes:
  takeover: "completed"
  asset_investigation: "in_progress"  # 变更：pending → in_progress
  claim_review: "completed"  # 变更：in_progress → completed
  creditor_meeting: "pending"
  distribution: "pending"
  reorganization_plan: "pending"
  report_submission: "pending"
```

---

## Phase 6：索引台账与看板更新

- 更新 portfolio-index.md（BANK-2026-001 阶段变更为财产调查）
- 更新 deadline-dashboard.md（新增财产状况报告提交 2026-08-10，剩余20天，🟡 即将到期）
- 更新 progress-tracker.md（更新履职节点状态）

---

## Phase 7：输出交付与更新日志

交付制品清单：

| 制品 | 路径 | 变更 |
|------|------|------|
| 元数据 | BANK-2026-001_XX科技/case-meta.yaml | 阶段/期限/履职节点更新 |
| 索引台账 | workspace_root/portfolio-index.md | BANK-2026-001 阶段更新 |
| 期限看板 | workspace_root/deadline-dashboard.md | 新增财产状况报告节点 |
| 进度跟踪 | workspace_root/progress-tracker.md | 履职节点状态更新 |
| 更新日志 | workspace_root/update-log.md | 新增 UPDATE 记录 |

更新日志条目：

```
## 2026-07-21

### 11:00 UPDATE BANK-2026-001
- 操作：补充案件材料 + 更新阶段
- 新增文件：债权申报表.pdf（2.3MB）、银行流水.xlsx（1.1MB）
- 更新阶段：债权审查 → 财产调查
- 新增期限：财产状况报告提交 2026-08-10
- 更新履职节点：债权审查 completed，财产调查 in_progress
```

---

## 关键提示

- 🟡 BANK-2026-001 财产状况报告提交截止 2026-08-10，剩余20天
- 建议优先完成银行流水分析，为财产状况报告做准备
