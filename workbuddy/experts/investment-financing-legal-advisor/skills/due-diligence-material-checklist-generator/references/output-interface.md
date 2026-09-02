# 输出数据格式（供下游消费）

> 本文件定义技能输出的 JSON Schema，供下游技能（如 company-equity-due-diligence）消费清单数据。

## JSON Schema（v1.2.0 列7→11+新增字段）

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "DDMaterialChecklist",
  "description": "尽调材料清单数据结构",
  "type": "object",
  "required": ["metadata", "items"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["scenario_id", "scenario_name", "target_company", "generated_date", "total_items"],
      "properties": {
        "scenario_id": {
          "type": "string",
          "enum": ["S-MNA", "S-PE", "S-IPO", "S-ASSET", "S-CROSSBORDER"]
        },
        "scenario_name": {
          "type": "string"
        },
        "target_company": {
          "type": "string"
        },
        "generated_date": {
          "type": "string",
          "format": "date"
        },
        "total_items": {
          "type": "integer",
          "minimum": 1
        },
        "modules_covered": {
          "type": "integer",
          "minimum": 1
        },
        "dd_depth": {
          "type": "string",
          "enum": ["快速", "标准", "深入"]
        },
        "checklist_version": {
          "type": "string",
          "description": "清单版本号，补充模式递增"
        },
        "is_supplement": {
          "type": "boolean",
          "description": "是否为补充清单（针对目标公司已回材料后的补充）"
        }
      }
    },
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "module", "name", "type", "necessity", "stage"],
        "properties": {
          "id": {
            "type": "string",
            "pattern": "^M[0-9]{1,2}-[0-9]{3}$",
            "description": "模块号-3位序号，如 M1-001"
          },
          "module": {
            "type": "string",
            "description": "模块名称"
          },
          "name": {
            "type": "string",
            "description": "资料名称"
          },
          "type": {
            "type": "string",
            "enum": ["证照", "合同", "决议", "财务报表", "其他"],
            "description": "资料类型"
          },
          "necessity": {
            "type": "string",
            "enum": ["必须", "推荐", "可选"],
            "description": "必需性"
          },
          "stage": {
            "type": "string",
            "enum": ["第一阶段", "第二阶段", "第三阶段"],
            "description": "提交阶段"
          },
          "dept": {
            "type": "string",
            "enum": ["财务部", "法务部", "人力资源部", "IT部", "行政部", "业务部"],
            "description": "存档/负责部门（v1.2.0新增）"
          },
          "receive_status": {
            "type": "string",
            "enum": ["未收", "已收", "部分提供", "拒绝提供"],
            "description": "接收状态（v1.2.0新增，初始默认'未收'）"
          },
          "receive_date": {
            "type": "string",
            "format": "date",
            "description": "收件日期（v1.2.0新增，初始为空）"
          },
          "provide_form": {
            "type": "string",
            "enum": ["", "原件", "复印件(盖章)", "电子版PDF", "电子版扫描件"],
            "description": "提供形式（v1.2.0新增，初始为空）"
          },
          "remark": {
            "type": "string",
            "description": "备注（特殊说明/法条依据）"
          },
          "acquisition_difficulty": {
            "type": "string",
            "enum": ["易", "中", "难", "极难"],
            "description": "材料获取难度（v1.2.0新增）"
          },
          "legal_basis": {
            "type": "string",
            "description": "法条依据（v1.2.0新增，关键材料项标注）"
          },
          "cross_validation_pair": {
            "type": "string",
            "description": "交叉验证配对材料项ID（v1.2.0新增）"
          }
        }
      }
    },
    "quality_report": {
      "type": "object",
      "properties": {
        "blocked_items": {
          "type": "array",
          "items": {"type": "string"}
        },
        "warning_items": {
          "type": "array",
          "items": {"type": "string"}
        },
        "passed": {
          "type": "boolean"
        }
      }
    },
    "cover_letter": {
      "type": "string",
      "description": "尽调材料索取函 Markdown文本（v1.2.0新增，当generate_cover_letter=true时生成）"
    },
    "dept_grouping": {
      "type": "object",
      "description": "按部门分组的材料清单（v1.2.0新增，供Sheet4生成使用）",
      "properties": {
        "财务部": {"type": "array", "items": {"$ref": "#/properties/items"}},
        "法务部": {"type": "array", "items": {"$ref": "#/properties/items"}},
        "人力资源部": {"type": "array", "items": {"$ref": "#/properties/items"}},
        "IT部": {"type": "array", "items": {"$ref": "#/properties/items"}},
        "行政部": {"type": "array", "items": {"$ref": "#/properties/items"}},
        "业务部": {"type": "array", "items": {"$ref": "#/properties/items"}}
      }
    }
  }
}
```

## 示例数据（v1.2.0 新增字段）

```json
{
  "metadata": {
    "scenario_id": "S-PE",
    "scenario_name": "PE/VC投资",
    "target_company": "XX科技有限公司",
    "generated_date": "2026-07-07",
    "total_items": 75,
    "modules_covered": 11,
    "dd_depth": "标准",
    "checklist_version": "1",
    "is_supplement": false
  },
  "items": [
    {
      "id": "M1-001",
      "module": "公司基本信息与历史沿革",
      "name": "营业执照副本",
      "type": "证照",
      "necessity": "必须",
      "stage": "第一阶段",
      "dept": "行政部",
      "receive_status": "未收",
      "receive_date": "",
      "provide_form": "",
      "remark": "需提供最新年检版本",
      "acquisition_difficulty": "易",
      "legal_basis": "《公司法》第32条",
      "cross_validation_pair": ""
    },
    {
      "id": "M2-014",
      "module": "股权结构与股东信息",
      "name": "对赌协议/估值调整协议",
      "type": "合同",
      "necessity": "必须",
      "stage": "第一阶段",
      "dept": "法务部",
      "receive_status": "未收",
      "receive_date": "",
      "provide_form": "",
      "remark": "含业绩承诺/补偿条款/回购条件（PE场景核心文件）",
      "acquisition_difficulty": "中",
      "legal_basis": "",
      "cross_validation_pair": "M3-010"
    },
    {
      "id": "M11-003",
      "module": "数据安全与个人信息保护",
      "name": "数据出境安全评估申报文件",
      "type": "证照",
      "necessity": "推荐",
      "stage": "第三阶段",
      "dept": "法务部",
      "receive_status": "未收",
      "receive_date": "",
      "provide_form": "",
      "remark": "如有数据出境，《数据安全法》第31条",
      "acquisition_difficulty": "难",
      "legal_basis": "《数据安全法》第31条",
      "cross_validation_pair": "M11-004"
    }
  ],
  "quality_report": {
    "blocked_items": [],
    "warning_items": ["QC-22: 关键材料项法条映射比例45%"],
    "passed": true
  }
}
```

## 下游消费说明

### company-equity-due-diligence 消费方式

1. 读取 `items` 数组，按 `module` 分组
2. 根据 `necessity` 确定核查优先级（必须→重点核查）
3. 根据 `stage` 安排尽调时间线
4. 根据 `cross_validation_pair` 执行交叉验证
5. 收到材料后，更新 `receive_status`/`receive_date`/`provide_form` 字段

### 材料状态回填协议（v1.2.0新增）

下游技能（或律师手动）回填状态时须遵守以下协议：

| 字段 | 更新方式 | 时机 | 冲突解决 |
|------|---------|------|---------|
| receive_status | 覆盖更新 | 收到/拒绝材料时 | 下游最新状态为准 |
| receive_date | 首次写入后不覆盖 | 首次收到材料时 | 保留首次日期 |
| provide_form | 覆盖更新 | 确认提供形式后 | 下游最新为准 |
| remark | 追加（不覆盖） | 需要补充说明时 | 追加";"分隔的新信息 |

### 其他下游技能消费方式

- **contract-ledger-manager**：可消费 M6 重大合同与债权债务模块的 items，生成合同台账
- **civil-evidence-analysis**：可将清单作为证据组织参考
- **data-compliance-checklist**（规划中）：可消费 M11 数据安全模块的数据
