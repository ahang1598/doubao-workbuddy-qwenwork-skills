# 示例1：新建清算案件（INIT 模式）

> 完整展示初始化破产清算案件的流程

---

## 用户输入

```
初始化破产案件。债务人：XX科技有限公司，程序类型：破产清算，
案号：（2026）粤03破申124号。受理法院：深圳市中级人民法院。
承办团队：张三（负责人）、赵六。
案件材料：D:\破产案卷\XX科技\ 下有若干PDF和Excel文件。
债权申报截止日：2026-08-20。
```

---

## Phase 1：意图识别与模式判定

- 识别关键词："初始化"、"破产案件"
- 模式判定：INIT
- 检测已有项目：扫描 workspace_root，无匹配案件

---

## Phase 2：输入解析与校验

解析结果：

```json
{
  "debtor_name": "XX科技有限公司",
  "procedure_type": "bankruptcy_liquidation",
  "case_number": "（2026）粤03破申124号",
  "court_name": "深圳市中级人民法院",
  "team_members": [
    {"name": "张三", "role": "负责人"},
    {"name": "赵六", "role": "成员"}
  ],
  "claim_deadline": "2026-08-20",
  "source_paths": ["D:\\破产案卷\\XX科技\\"],
  "operation_mode": "INIT"
}
```

校验通过。

---

## Phase 3：操作计划生成与确认

展示操作计划：

```
【操作计划】
模式：INIT
目标：BANK-2026-002_XX科技
将创建：
- 目录：01-接管材料/02-债权申报/03-财产调查/04-债权人会议/
        05-履职报告/06-程序文件/07-工作底稿/08-财产变现方案/
        09-分配方案/10-分配执行（共10个一级目录）
- 文件：case-meta.yaml
将复制：
- D:\破产案卷\XX科技\ → 01-接管材料/（约150个文件）
是否确认执行？
```

用户确认。

---

## Phase 4：文件系统操作执行

- 创建目录结构：10个一级目录 + 26个二级目录
- 复制文件：156个（PDF 98个，Excel 32个，Word 26个）
- 生成 case-meta.yaml

---

## Phase 5：制品生成与写入

生成 case-meta.yaml：

```yaml
case_id: "BANK-2026-002"
case_number: "（2026）粤03破申124号"
debtor_name: "XX科技有限公司"
debtor_short_name: "XX科技"
procedure_type: "bankruptcy_liquidation"
procedure_type_cn: "破产清算"
court_name: "深圳市中级人民法院"
filing_date: "2026-07-10"
current_stage: "asset_investigation"
stage_cn: "财产调查"
status: "active"
team_members:
  - name: "张三"
    role: "负责人"
  - name: "赵六"
    role: "成员"
deadlines:
  claim_deadline: "2026-08-20"
  first_creditor_meeting: ""
  reorganization_plan_deadline: ""
  distribution_plan_announcement: ""
  duty_report_deadline: ""
key_concerns: []
created_at: "2026-07-21T10:00:00"
updated_at: "2026-07-21T10:00:00"
urgency: "normal"
```

---

## Phase 6：索引台账与看板更新

- 更新 portfolio-index.md（新增 BANK-2026-002）
- 更新 deadline-dashboard.md（新增债权申报截止 2026-08-20）
- 更新 progress-tracker.md（新增案件进度）

---

## Phase 7：输出交付与更新日志

交付制品清单：

| 制品 | 路径 |
|------|------|
| 案件目录 | workspace_root/BANK-2026-002_XX科技/ |
| 元数据 | workspace_root/BANK-2026-002_XX科技/case-meta.yaml |
| 索引台账 | workspace_root/portfolio-index.md |
| 期限看板 | workspace_root/deadline-dashboard.md |
| 进度跟踪 | workspace_root/progress-tracker.md |
| 更新日志 | workspace_root/update-log.md |

更新日志条目：

```
## 2026-07-21

### 10:00 INIT BANK-2026-002
- 操作：初始化破产清算案件
- 债务人：XX科技有限公司
- 创建目录：10个一级目录 + 26个二级目录
- 复制文件：156个
- 生成制品：case-meta.yaml
```

---

## 关键提示

- 债权申报截止日 2026-08-20，剩余30天，预警级别 🟡 即将到期
- 建议尽快启动债权申报公告和通知
