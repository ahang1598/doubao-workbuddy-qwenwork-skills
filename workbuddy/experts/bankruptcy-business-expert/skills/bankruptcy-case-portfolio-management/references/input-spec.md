# 输入规格

> bankruptcy-case-portfolio-management 技能的输入参数详细定义

---

## 1. 输入模式

本技能支持三种输入模式，自动识别：

| 模式 | 触发方式 | 典型场景 |
|------|----------|----------|
| 自然语言 | 用户描述需求 | "初始化XX科技破产清算案件，材料在D盘" |
| 参数化 | 用户按参数格式提供 | `debtor_name=XX科技, procedure_type=liquidation` |
| 混合式 | 部分自然语言+部分参数 | "补充XX案材料，source_paths=D:\新到材料\" |

---

## 2. 必填参数

### 2.1 `debtor_name`

- **类型**：字符串
- **说明**：债务人名称（全称），用于案件目录命名和台账登记
- **示例**：`"XX科技有限公司"`、`"XX房地产开发有限公司"`
- **校验**：非空，长度≤100字符

### 2.2 `procedure_type`

- **类型**：枚举字符串
- **说明**：破产程序类型，决定目录模板路由
- **取值**：
  - `bankruptcy_liquidation`：破产清算
  - `reorganization`：破产重整
  - `settlement`：破产和解
- **校验**：必须在枚举值范围内，否则提示用户确认

### 2.3 `source_paths`

- **类型**：字符串数组
- **说明**：案件文件来源路径列表（文件或文件夹路径），技能将从这些路径复制文件到案件目录
- **示例**：`["D:\\破产案卷\\XX科技\\"]`、`["D:\\债权申报表.pdf", "D:\\银行流水.xlsx"]`
- **校验**：路径必须存在且可读；空数组提示用户确认是否仅创建空目录结构

---

## 3. 推荐参数

### 3.1 `case_number`

- **类型**：字符串
- **说明**：案号，用于台账登记和文件名标识
- **示例**：`"（2026）粤03破申123号"`
- **格式**：建议遵循法院案号格式

### 3.2 `court_name`

- **类型**：字符串
- **说明**：受理法院全称
- **示例**：`"深圳市中级人民法院"`

### 3.3 `team_members`

- **类型**：对象数组
- **说明**：承办团队成员列表
- **结构**：`[{name: "张三", role: "负责人"}, {name: "李四", role: "成员"}]`
- **角色枚举**：负责人/成员/助理/外部顾问

### 3.4 `claim_deadline`

- **类型**：日期字符串（YYYY-MM-DD）
- **说明**：债权申报截止日
- **用途**：期限看板关键节点

### 3.5 `first_creditor_meeting`

- **类型**：日期字符串（YYYY-MM-DD）
- **说明**：第一次债权人会议日期
- **用途**：期限看板关键节点

### 3.6 `key_concerns`

- **类型**：字符串数组
- **说明**：重点关注事项，用于履职汇总风险提示
- **示例**：`["担保债权审查", "在建工程处置", "职工安置"]`

---

## 4. 选填参数

### 4.1 `workspace_root`

- **类型**：字符串（路径）
- **说明**：案件工作空间根目录路径
- **默认**：系统默认路径（如 `~/bankruptcy-workspace/` 或用户首次指定后记忆）
- **校验**：路径必须可写；不存在时自动创建

### 4.2 `case_id_override`

- **类型**：字符串
- **说明**：手动指定案件ID（跳过自动检测）
- **用途**：强制关联到已有案件，或指定特定ID格式
- **格式**：建议 `BANK-{年份}-{序号}` 或 UUID

### 4.3 `urgency`

- **类型**：枚举字符串
- **说明**：案件紧急度
- **取值**：`urgent`（紧急）/`medium`（中等）/`normal`（正常）
- **默认**：`normal`

### 4.4 `operation_mode`

- **类型**：枚举字符串
- **说明**：强制指定操作模式（跳过自动检测）
- **取值**：`INIT`（新建）/`UPDATE`（更新）/`PORTFOLIO`（台账）/`DEADLINE`（期限）/`PROGRESS`（进度）/`DUTY_SUMMARY`（履职汇总）

---

## 5. 多案件管理专用参数

当 `operation_mode` 为 `PORTFOLIO`/`DEADLINE`/`PROGRESS`/`DUTY_SUMMARY` 时：

### 5.1 `filter_criteria`

- **类型**：对象
- **说明**：筛选条件
- **结构**：
  ```json
  {
    "debtor_name": "XX",
    "procedure_type": "liquidation",
    "stage": "claim_review",
    "team_member": "张三",
    "status": "active"
  }
  ```

### 5.2 `export_format`

- **类型**：枚举字符串
- **说明**：导出格式
- **取值**：`markdown`（默认）/`excel`/`yaml`

---

## 6. 输入校验规则

| 规则 | 校验内容 | 违反处理 |
|------|----------|----------|
| V1 | debtor_name 非空且≤100字符 | 阻断，提示用户补充 |
| V2 | procedure_type 在枚举范围内 | 阻断，提示用户确认 |
| V3 | source_paths 路径存在且可读 | 阻断，提示路径无效 |
| V4 | 日期格式为 YYYY-MM-DD | 警告，尝试自动转换 |
| V5 | workspace_root 可写 | 阻断，提示权限不足 |
| V6 | team_members 结构正确 | 警告，忽略无效成员 |

---

## 7. 输入示例

### 7.1 最简输入（INIT）

```
初始化破产案件。债务人：XX科技有限公司，程序类型：破产清算，
案件材料在 D:\破产案卷\XX科技\。
```

解析结果：
```json
{
  "debtor_name": "XX科技有限公司",
  "procedure_type": "bankruptcy_liquidation",
  "source_paths": ["D:\\破产案卷\\XX科技\\"],
  "operation_mode": "INIT"
}
```

### 7.2 完整输入（INIT）

```json
{
  "debtor_name": "XX房地产开发有限公司",
  "procedure_type": "reorganization",
  "case_number": "（2026）粤03破申123号",
  "court_name": "深圳市中级人民法院",
  "team_members": [
    {"name": "张三", "role": "负责人"},
    {"name": "李四", "role": "成员"},
    {"name": "王五", "role": "成员"}
  ],
  "claim_deadline": "2026-08-15",
  "first_creditor_meeting": "2026-09-01",
  "key_concerns": ["担保债权审查", "在建工程处置"],
  "source_paths": ["D:\\破产案卷\\XX房产\\"],
  "urgency": "urgent"
}
```

### 7.3 多案件查询（PORTFOLIO）

```
生成我手上所有破产案件的台账和期限看板。
```

解析结果：
```json
{
  "operation_mode": "PORTFOLIO",
  "filter_criteria": {},
  "export_format": "markdown"
}
```

### 7.4 筛选查询（DEADLINE）

```json
{
  "operation_mode": "DEADLINE",
  "filter_criteria": {
    "status": "active",
    "team_member": "张三"
  }
}
```
