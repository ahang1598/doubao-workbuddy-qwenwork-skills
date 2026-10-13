---
name: shared
description: Shared API references for AI Table (钉钉表格) script and plugin development. Contains comprehensive documentation for Base, Sheet, Field, Record, View, Input, Output, and UI modules. This skill serves as a common knowledge base for other AI Table related skills.
license: MIT
metadata:
  author: AI Table Team
  version: 1.0.0
  category: reference
  tags: [ai-table, api-reference, shared, documentation]
---

# AI Table Shared References

This skill contains shared API documentation and references for AI Table (钉钉表格) script and plugin development. It serves as a common knowledge base that can be referenced by other skills.

## Purpose

- **Centralized Documentation**: Maintain a single source of truth for AI Table API documentation
- **Cross-Skill Sharing**: Allow multiple skills (e.g., ai-script-generator, ai-plugin-builder) to reference the same API docs
- **Consistency**: Ensure all skills use the same, up-to-date API information
- **Reduced Maintenance**: Update once, benefit everywhere

## Directory Structure

```
shared/
├── GUIDE.md                          # This file
└── references/
    └── api/
        ├── 读写AI 表格模型.md          # Overview of AI Table data model
        ├── interface/
        │   ├── API 类型定义.md         # API type definitions
        │   └── 字段类型结构.md         # Field type structures
        └── modules/
            ├── Base 模块.md            # Base module API
            ├── Sheet 模块.md           # Sheet (data table) operations
            ├── Field 模块.md           # Field operations
            ├── Record 模块.md          # Record operations
            ├── View 模块.md            # View operations
            ├── GridView 表格视图.md    # Grid view specific API
            ├── Input模块.md            # User input API
            ├── Output模块.md           # Output/logging API
            ├── UI 模块.md              # UI components API
            └── Field api/              # Field type specific APIs
                ├── TextField 文本字段.md
                ├── NumberField 数字字段.md
                ├── DateField 日期字段.md
                ├── SingleSelectField 单选字段.md
                ├── MultiSelectField 多选字段.md
                ├── AttachmentField 附件字段.md
                ├── UserField 人员字段.md
                ├── CurrencyField 货币字段.md
                ├── RatingField 评分字段.md
                ├── ProgressField 进度字段.md
                └── ... (more field types)
```

## How to Reference

Other skills can reference these shared documents by using relative paths:

### In the skill entry (`SKILL.md`) or a guide (`GUIDE.md`)

```markdown
## API References

For detailed API documentation, consult the shared references:
- Base operations: `../shared/references/api/modules/Base 模块.md`
- Sheet operations: `../shared/references/api/modules/Sheet 模块.md`
- Field operations: `../shared/references/api/modules/Field 模块.md`
- Input API: `../shared/references/api/modules/Input模块.md`
- Type definitions: `../shared/references/api/interface/API 类型定义.md`
```

### In Code Generation

When generating scripts or plugins, always consult the appropriate module documentation to ensure API compliance.

## Module Overview

### Base Module
Entry point for accessing sheets, views, and global operations.
- `Base.getActiveSheet()` - Get currently active sheet
- `Base.getSheets()` - Get all sheets
- `Base.isFieldOfType()` - Type-safe field checking
- `Base.getCurrentUser()` - Current user info (`Promise<UserCellValue | null>`)
- `Base.getCorpId()` / `Base.getDentryUuid()` - Corp / document identifiers
- `Base.ui` - UI module (toast / selection / highlight / record detail)

### Sheet Module
Data table operations including field management, view management, and record operations.
- `sheet.getFields()` - Get all fields
- `sheet.insertField()` - Add new field
- `sheet.getRecordsAsync()` - Load records with pagination
- `sheet.insertRecordsAsync()` - Batch insert records
- `sheet.updateRecordsAsync()` - Batch update records

### Field Module
Field-specific operations and type-specific APIs.
- Common: `getName()`, `getType()`, `getId()`, `getDesc()`, `getSync()`
- Type-specific: `getOptions()` (select), `getValueAsync()`, `setValueAsync()`, `getFormatter()` (number/progress), `getDateFormat()` (date)
- ⚠️ Sidebar `service.ts` can use `sheet.getField<T>()`; **script plugins cannot** — use `Base.isFieldOfType()` instead

### Record Module
Individual record operations.
- `getCellValue()` - Get cell value
- `getCellValues()` - Get all cell values
- `getId()` - Get record ID

### Input Module
User interaction and form inputs.
- `Input.textAsync()` - Text input
- `Input.selectAsync()` - Selection input
- `Input.formAsync()` - Complex form with multiple fields

### Output Module
Logging and user feedback. **Script plugin only** — not available in a sidebar plugin's Script Service.
- `Output.log()` - General logging
- `Output.info()` - Info messages
- `Output.success()` - Success messages
- `Output.error()` - Error messages
- `Output.table()` - Table output
- `Output.clear()` - Clear the run panel

### UI Module
Toast notifications and selection helpers.
- `Base.ui.toast()` - Show toast notification
- `Base.ui.getSelection()` - Active cell position
- `Base.ui.getSelectedRecordIds()` - Record IDs the user actually selected
- `Base.ui.showRecordDetail()` - Open record detail (`RecordDetailType.MODAL` / `SIDE_PANEL`)

## Usage Guidelines

1. **Always Consult Before Coding**: Before writing any AI Table script, consult the relevant module documentation
2. **Type Safety**: Use `Base.isFieldOfType()` for type-safe field operations
3. **Pagination**: Use cursor-based pagination for loading large datasets
4. **Batch Operations**: Use batch methods for better performance. Script/sidebar plugin limits are **insert 1000 / update 500 / delete 500 / `getRecordsAsync` pageSize 500** (the 500/100/100/100 figures belong to the REST OpenAPI channel, not to plugins)
5. **Error Handling**: Always wrap async operations in try-catch blocks

## Maintenance

When updating API documentation:
1. Update the relevant file in `references/api/`
2. All skills referencing this shared resource will automatically use the updated documentation
3. No need to update individual skills unless the API changes significantly
