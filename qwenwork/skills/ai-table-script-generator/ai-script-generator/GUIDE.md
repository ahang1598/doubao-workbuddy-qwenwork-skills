---
name: ai-script-generator
description: Generates production-ready scripts for AI Table plugin development. Use when user asks to "create a script", "generate AI table code", "write automation script", or references specific operations like "field manipulation", "record operations", "data validation". Supports field types: text, number, date, singleSelect, multipleSelect, attachment, url, user, link, rating, progress, currency, etc. Outputs complete TypeScript code with proper API calls and manifest.json.
license: MIT
metadata:
  author: AI Table Team
  version: 1.0.0
  category: automation
  tags: [ai-table, script-generation, automation]
---

# AI Table Script Generator

Generates production-ready TypeScript scripts for AI Table (钉钉表格) plugin development. All generated scripts follow strict API compliance and include comprehensive error handling.

## Core Principles

1. **API Compliance**: Strictly follow AI Table API definitions in `references/api/` and `../shared/references/api` directory
2. **No Fabrication**: Never invent APIs or methods - only use documented interfaces
3. **Production Ready**: Include proper error handling, user feedback, and batch processing
4. **Button Trigger Support**: Scripts should support button field triggering using `Input.formAsync` with `Record` type when applicable
5. **Manifest Only When Needed**: Generate `manifest.json` only when user confirms script works and wants to publish it
6. **Script Naming**: Provide concise script names (≤10 characters) and descriptions (≤100 characters)

## Advanced Features

### Network Requests

Script plugins support making HTTP requests using the standard `fetch` API. This allows integration with external services, APIs, and data sources.

**Requirements**:
- External interfaces must support Cross-Origin Resource Sharing (CORS)
- Handle authentication (API keys, tokens, signatures) securely
- Implement proper error handling for network failures

**Example - Fetching External Data**:
```typescript
async function fetchExternalData() {
  try {
    const response = await fetch('https://api.example.com/data', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer YOUR_TOKEN'
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    Output.log('Successfully fetched data:', data);
    return data;
  } catch (error) {
    Output.error(`Network request failed: ${error.message}`);
    throw error;
  }
}
```

**Example - API Signature (Aliyun RAM)**:
For advanced use cases like signed API requests, refer to the example in `.skills/ai-script-generator/references/examples/network-requests/aliyun-ram-users.ts` which demonstrates:
- HMAC-SHA1 signature generation
- URL encoding and parameter sorting
- Pagination handling
- Crypto API usage

**Key Points**:
- Always use try-catch for network operations
- Validate response status before processing
- Handle rate limiting and retry logic appropriately
- Never hardcode sensitive credentials in generated scripts
- Use Input methods to collect authentication data from users

## Workflow

### Phase 1: Understand User Intent
Analyze user request to determine:
- **Operation type**: CRUD operations, data transformation, validation, etc.
- **Target objects**: Sheets, Fields, Records, Views
- **Data types**: Text, Number, Date, Selection, Link, Attachment, etc.
- **Button trigger requirement**: Whether the script should support button field triggering
- **Output format**: Script only or Script + Manifest + Description

**Always ask clarifying questions if intent is ambiguous:**
- "Which sheet should the script operate on?"
- "Which fields are involved?"
- "What constitutes a successful outcome?"
- "Should this script support button field triggering?"

### Phase 2: Consult API References
Before writing code, consult relevant API documentation in `references/api` and `../shared/references/api/`:

**For Field Operations:**
- `../shared/references/api/modules/Field 模块.md` - General field API
- `../shared/references/api/modules/Field api/[FieldType].md` - Type-specific methods

**For Record Operations:**
- `../shared/references/api/modules/Record 模块.md` - Record read/write
- `../shared/references/api/modules/Sheet 模块.md` - Batch operations

**For Input API (including Button Trigger):**
- `../shared/references/api/modules/Input模块.md` - Complete Input API including Record type for button triggers

**For Type Definitions:**
- `../shared/references/api/interface/API 类型定义.md` - Type structures
- `../shared/references/api/interface/字段类型结构.md` - Field value types

**Critical Rule**: Never use undocumented APIs. If a method is not in the documentation, it does not exist.

### Phase 3: Generate Script Code

#### Template Structure
```typescript
async function main() {
  try {
    // 1. User Input Collection (use Input.formAsync for complex configurations)
    const formResult = await Input.formAsync('脚本配置', [
      // Form items for sheet, fields, parameters
    ]);

    // 2. Validation
    // Validate field types, data formats, permissions
    
    // 3. Data Processing
    // Load records, process data, generate updates
    
    // 4. Batch Operations
    // Use batch processing (script/sidebar plugin: insert ≤ 1000, update/delete ≤ 500 per call)
    
    // 5. User Feedback
    Output.log('操作完成');
  } catch (error) {
    if (error instanceof Error) {
      Output.error(`执行过程中发生错误: ${error.message}`);
    } else {
      Output.error(`执行过程中发生未知错误`);
    }
  }
}

await main();
```

#### Common Patterns

**Pattern 1: Single Field Value Update**
```typescript
const field = sheet.getField('fieldName');
if (Base.isFieldOfType(field, 'text')) {
  await field.setValueAsync(recordId, 'new value');
}
```

**Pattern 2: Batch Record Processing**
```typescript
const updates = [];
for (const record of records) {
  updates.push({
    id: record.getId(),
    fields: {
      [fieldId]: processedValue
    }
  });
}

// Batch update (script/sidebar plugin: updateRecordsAsync accepts up to 500 per call)
const batchSize = 500;
while (updates.length > 0) {
  const batch = updates.slice(0, batchSize);
  await sheet.updateRecordsAsync(batch);
  updates.splice(0, batchSize);
}
```

**Pattern 3: Field Type Checking**
```typescript
// Always use Base.isFieldOfType for type safety
if (Base.isFieldOfType(field, 'singleSelect')) {
  const options = field.getOptions();
  // Type-safe operations
}
```

**Pattern 4: Loading All Records**
```typescript
const allRecords = [];
let hasMore = true;
let cursor = "";

while (hasMore) {
  const result = await sheet.getRecordsAsync({
    pageSize: 500,
    cursor: cursor,
  });
  allRecords.push(...result.records);
  hasMore = result.hasMore;
  cursor = result.cursor;
}
```

**Pattern 5: Button Trigger Support (Record Type)**
```typescript
// 当脚本通过按钮字段触发时，使用 Record 类型可以自动填充当前记录
const formResult = await Input.formAsync('脚本配置', [
  {
    type: 'sheet',
    key: 'sheet',
    option: { label: '选择数据表' },
    required: true
  },
  {
    type: 'record',
    key: 'record',
    option: { 
      label: '选择记录',
      referenceSheet: 'sheet'  // 必须引用 Sheet 表单项
    },
    required: true
  }
]);

// 当通过按钮触发时，sheet 和 record 会自动填充为当前上下文
// 这样脚本既支持手动运行，也支持按钮触发
const sheet = formResult.sheet;
const record = formResult.record;
```

**按钮触发说明**：
- 使用 `type: 'record'` 的表单项可以让脚本支持按钮字段触发
- 当用户点击按钮运行脚本时，系统会自动填充：
  - Sheet：按钮所在的数据表
  - Record：点击按钮的那一行记录
- 如果所有必填项都能自动填充，表单会自动提交，无需用户手动操作
- 如果有必填项无法自动填充，表单会正常弹出，已识别的项会预先填入

#### Field-Specific Value Types

> ⚠️ 下面括号里标的是 **声明类型**（脚本编辑器会按它做类型检查）。部分字段运行时更宽容，但传非声明类型会在编辑器里报红，**优先按声明类型生成**。

**Text Field**: `string`
```typescript
await textField.setValueAsync(recordId, 'text value');
```

**Number Field**: `number`
```typescript
await numberField.setValueAsync(recordId, 123);
// 运行时也接受可转数字的字符串（'123'），但声明类型是 number，不推荐
```

**Date Field**: `number`（毫秒级 Unix 时间戳）
```typescript
await dateField.setValueAsync(recordId, Date.now());
// 运行时也接受 dayjs 可解析的日期字符串（'2025-01-01'），但声明类型是 number，不推荐
```

**Single Select**: `string`（选项 ID）
```typescript
// 推荐：先 getOptions() 找到选项再传 id
const option = singleSelectField.getOptions().find(o => o.name === 'Option Name');
if (option) await singleSelectField.setValueAsync(recordId, option.id);

// 运行时先按 id 匹配，匹配不上再按选项名匹配，所以直接传选项名也能生效
await singleSelectField.setValueAsync(recordId, 'Option Name');

// ❌ 脚本插件不能传 { id } / { name } 对象形式，会抛
//    `the value '[object Object]' is invalid for field 'xxx'`
//    对象形式只有边栏插件（appType = ADDON）支持
```

**Multiple Select**: `string | string[]`（选项 ID）
```typescript
await multiSelectField.setValueAsync(recordId, ['optionId1', 'optionId2']);
// 字段类型字面量是 'multipleSelect'（不是 'multiSelect'）
// 同样：对象形式只有边栏插件支持
```

**Attachment**: `IOpenFile | IOpenFile[] | AttachmentValue | AttachmentValue[]`
```typescript
await attachmentField.setValueAsync(recordId, {
  name: 'file.pdf',
  type: 'application/pdf',
  size: 1024,
  content: base64Content   // string | ArrayBuffer
});
// 读取时 getValueAsync() 返回 AttachmentValue[]（每项含 type / filename / url / size? / resourceId?）
```

**URL**: `string | {link: string, text?: string}`
```typescript
await urlField.setValueAsync(recordId, 'https://example.com');
await urlField.setValueAsync(recordId, {
  link: 'https://example.com',
  text: 'Example Site'
});
```

**User Field**: `UserCellValue | UserCellValue[]`
```typescript
await userField.setValueAsync(recordId, [
  { userId: 'user123' },
  { unionId: 'union456' }
]);
// 可用的写入键：userId / unionId / uid / jobNumber / extContactUserId
```

**Link Fields (Uni/Bidirectional)**: `{linkedRecordIds: string[]}`
```typescript
await linkField.setValueAsync(recordId, {
  linkedRecordIds: ['rec1', 'rec2']
});
```

**Rating/Progress**: `number`
```typescript
await ratingField.setValueAsync(recordId, 4);        // 必须在 getMin()~getMax() 之间
await progressField.setValueAsync(recordId, 75);     // 取值范围由 getMin()/getMax() 决定
```

**Currency**: `number | string`
```typescript
await currencyField.setValueAsync(recordId, 99.99);
```

**Checkbox**: `boolean`
```typescript
await checkboxField.setValueAsync(recordId, true);
```

### Phase 4: Generate Script Name and Description

After generating the script, provide:
- **Script Name**: Concise name ≤ 10 Chinese characters
- **Description**: Detailed description ≤ 100 Chinese characters explaining functionality and use cases

**Example**:
```
脚本名称：邮箱验证
脚本描述：批量验证邮箱地址格式，标记有效和无效邮箱
```

### Phase 5: Generate Manifest (When User Requests Publication)

**IMPORTANT**: Only generate `manifest.json` when user explicitly confirms:
1. The script works correctly
2. They want to publish/use it as a plugin
3. Whether it should be visible in button field configuration

#### Complete Manifest Generation Example

When generating the manifest, you must properly escape the script code using `JSON.stringify()`:

```javascript
// Step 1: Generate the TypeScript script code
const scriptCode = `async function main() {
  try {
    const formResult = await Input.formAsync('配置', [
      {
        type: 'sheet',
        key: 'sheet',
        option: { label: '选择数据表' },
        required: true
      }
    ]);

    const sheet = formResult.sheet;
    Output.log('操作完成');
  } catch (error) {
    Output.error(\`执行过程中发生错误: \${error.message}\`);
  }
}

await main();`;

// Step 2: Escape the script code using JSON.stringify()
const escapedScriptCode = JSON.stringify(scriptCode);

// Step 3: Build the complete manifest
const manifest = {
  "extensionName": "script-example",
  "extensionType": "side_view",
  "classifications": ["script"],
  "schemaVersion": "v1",
  "icon": {
    "light": "https://img.alicdn.com/imgextra/i1/O1CN01mShWFK21gvUBZei7V_!!6000000007015-55-tps-32-32.svg"
  },
  "i18nDesc": {
    "en-US": "Example script description",
    "zh-CN": "示例脚本描述"
  },
  "i18nName": {
    "en-US": "Example Script",
    "zh-CN": "示例脚本"
  },
  "i18nIntroduction": {
    "en-US": "This is an example script",
    "zh-CN": "这是一个示例脚本"
  },
  "i18nVideo": {
    "en-US": "",
    "zh-CN": ""
  },
  "i18nImage": {
    "en-US": "",
    "zh-CN": ""
  },
  "i18nHelpLink": {},
  "i18nDeveloper": {
    "en-US": "DingTalk",
    "zh-CN": "钉钉"
  },
  "manifest": {
    "base": {
      "scriptCode": escapedScriptCode,
      "buttonTrigger": true
    }
  },
  "privacyAgreement": "{}",
  "agreement": "{}"
};

// Step 4: Convert to JSON string (no need for extra stringify on manifest field)
const manifestJson = JSON.stringify(manifest, null, 2);
```

**Key Points**:
- The `scriptCode` value in `manifest.base` must be a JSON string (already escaped)
- The entire `manifest` field should be a JSON object, not a string
- Do NOT double-escape the script code or the manifest field

#### Manifest Structure
```json
{
  "extensionName": "script-unique-name",
  "extensionType": "side_view",
  "classifications": ["script"],
  "schemaVersion": "v1",
  "icon": {
    "light": "https://img.alicdn.com/imgextra/i1/O1CN01mShWFK21gvUBZei7V_!!6000000007015-55-tps-32-32.svg"
  },
  "i18nDesc": {
    "en-US": "Brief description in English",
    "zh-CN": "中文描述"
  },
  "i18nName": {
    "en-US": "Script Name",
    "zh-CN": "脚本名称"
  },
  "i18nIntroduction": {
    "en-US": "Detailed introduction in English",
    "zh-CN": "详细的中文介绍"
  },
  "i18nVideo": {
    "en-US": "",
    "zh-CN": ""
  },
  "i18nImage": {
    "en-US": "",
    "zh-CN": ""
  },
  "i18nHelpLink": {},
  "i18nDeveloper": {
    "en-US": "DingTalk",
    "zh-CN": "钉钉"
  },
  "manifest": {
    "base": {
      "scriptCode": "ESCAPED_SCRIPT_CODE_HERE",
      "buttonTrigger": true  // Set to true if script supports button triggering
    }
  },
  "privacyAgreement": "{}",
  "agreement": "{}"
}
```

#### Critical Manifest Generation Rules

1. **Script Code Escaping**: The `manifest.base.scriptCode` field must contain the script code as a JSON string using `JSON.stringify()`. This means:
   - All double quotes (`"`) must be escaped as `\"`
   - All backslashes (`\`) must be escaped as `\\`
   - Newlines must be escaped as `\n`

   **Example**:
   ```javascript
   const scriptCode = `async function main() {
     Output.log("Hello World");
   }`;
   
   // When generating manifest, use:
   const escapedScriptCode = JSON.stringify(scriptCode);
   // Result: "async function main() {\n  Output.log(\"Hello World\");\n}"
   ```

2. **Button Trigger Configuration**:
   - If the script uses `Input.formAsync` with `Record` type to support button triggering
   - Ask user: "Should this script be visible in button field configuration?"
   - If YES: Set `"buttonTrigger": true` in `manifest.base`
   - If NO: Omit `"buttonTrigger"` field

3. **Reference Official Examples**: Check `references/examples/manifest/` directory for official manifest examples:
   - `checkdup.manifest.json` - Example with buttonTrigger
   - `vote.manifest.json` - Example of button-triggered script
   - `meta.manifest.json` - Example without buttonTrigger

### Phase 6: Generate Description File (Optional)

## Examples

### Example 1: Email Validation Script
**User Request**: "Create a script to validate email addresses"

**Generated Script**:
```typescript
async function main() {
  try {
    const formResult = await Input.formAsync('邮箱验证配置', [
      {
        type: 'sheet',
        key: 'sheet',
        option: { label: '选择数据表' },
        required: true
      },
      {
        type: 'field',
        key: 'emailField',
        option: { label: '选择邮箱字段', referenceSheet: 'sheet' },
        required: true
      }
    ]);

    const sheet = formResult.sheet;
    const emailField = formResult.emailField;

    // Create validation result field
    let validationField = sheet.getField('邮箱验证结果');
    if (!validationField) {
      validationField = sheet.insertField('邮箱验证结果', 'text');
    }

    const emailRegex = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$/;

    const result = await sheet.getRecordsAsync({ pageSize: 500 });
    const updates = [];

    for (const record of result.records) {
      const email = record.getCellValue(emailField.getName());
      const isValid = typeof email === 'string' && emailRegex.test(email);

      updates.push({
        id: record.getId(),
        fields: {
          '邮箱验证结果': isValid ? '有效' : '无效'
        }
      });
    }

    // Batch update
    while (updates.length > 0) {
      const batch = updates.slice(0, 50);
      await sheet.updateRecordsAsync(batch);
      updates.splice(0, 50);
    }

    Output.log(`邮箱验证完成，共处理 ${result.records.length} 条记录`);
  } catch (error) {
    Output.error(`执行过程中发生错误: ${error.message}`);
  }
}

await main();
```

### Example 2: Bulk Text Replace
**User Request**: "Replace all instances of text in a field"

**Generated Script**:
```typescript
async function main() {
  try {
    const formResult = await Input.formAsync('查找替换配置', [
      { type: 'sheet', key: 'sheet', option: { label: '数据表' }, required: true },
      { type: 'field', key: 'field', option: { label: '文本字段', referenceSheet: 'sheet' }, required: true },
      { type: 'text', key: 'findText', option: { label: '查找文本' }, required: true },
      { type: 'text', key: 'replaceText', option: { label: '替换文本' }, required: false }
    ]);

    const sheet = formResult.sheet;
    const field = formResult.field;
    const findText = formResult.findText;
    const replaceText = formResult.replaceText || '';

    if (field.getType() !== 'text') {
      Output.error('只能对文本字段进行查找替换');
      return;
    }

    const result = await sheet.getRecordsAsync({ pageSize: 500 });
    const updates = [];

    for (const record of result.records) {
      const originalValue = record.getCellValue(field.getName());
      if (typeof originalValue !== 'string') continue;

      const newValue = originalValue.replace(new RegExp(findText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), replaceText);

      if (originalValue !== newValue) {
        updates.push({
          id: record.getId(),
          fields: { [field.getName()]: newValue }
        });
      }
    }

    while (updates.length > 0) {
      const batch = updates.slice(0, 50);
      await sheet.updateRecordsAsync(batch);
      updates.splice(0, 50);
    }

    Output.log(`成功替换 ${updates.length} 条记录`);
  } catch (error) {
    Output.error(`执行过程中发生错误: ${error.message}`);
  }
}

await main();
```

### Example 3: Button-Triggered Voting Script
**User Request**: "Create a voting script that can be triggered by a button to increment vote count"

**Generated Script**:
```typescript
async function main() {
  try {
    const formResult = await Input.formAsync('投票设置', [
      {
        type: 'sheet',
        key: 'targetSheet',
        option: {
          label: '选择目标数据表',
        },
        required: true,
      },
      {
        type: 'record',
        key: 'targetRecord',
        option: {
          label: '选择记录',
          referenceSheet: 'targetSheet',
        },
        required: true,
      }
    ]);
    
    const targetSheet = formResult.targetSheet;
    const record = formResult.targetRecord;
    
    // Check or create vote result field
    let voteField = targetSheet.getField('投票结果');
    if (!voteField) {
      voteField = targetSheet.insertField('投票结果', 'number');
      Output.info('已创建「投票结果」数字字段');
    } else if (!Base.isFieldOfType(voteField, 'number')) {
      Output.error('已存在名为「投票结果」的字段，但不是数字类型');
      return;
    }
    
    // Get current vote value
    let currentVoteValue = await voteField.getValueAsync(record.getId());
    currentVoteValue = Number(currentVoteValue);
    currentVoteValue = Number.isNaN(currentVoteValue) ? 0 : currentVoteValue;
    
    // Increment and update
    const newVoteValue = currentVoteValue + 1;
    const success = await voteField.setValueAsync(record.getId(), newVoteValue);
    
    if (success) {
      Output.info(`投票成功！当前投票数: ${newVoteValue}`);
      Base.ui.toast({ type: 'success', message: '投票成功，已+1' });
    } else {
      Output.error('投票失败，请稍后重试');
      Base.ui.toast({ type: 'error', message: '投票失败' });
    }
  } catch (error) {
    Output.error(`执行过程中发生错误: ${error.message}`);
  }
}

await main();
```

**Button Trigger Notes**:
- This script uses `type: 'record'` in `Input.formAsync`
- When triggered by button, `targetSheet` and `targetRecord` are automatically filled
- No user interaction needed when button-triggered
- The same script works for both manual execution and button triggering

## Common Operations Reference

### Input API
```typescript
// Text input
const text = await Input.textAsync('请输入文本');

// Select from options
const choice = await Input.selectAsync('请选择', ['选项A', '选项B', '选项C']);

// Complex form
const formResult = await Input.formAsync('配置', [
  { type: 'sheet', key: 'sheet', option: { label: '数据表' }, required: true },
  { type: 'field', key: 'field', option: { label: '字段', referenceSheet: 'sheet' }, required: true },
  { type: 'record', key: 'record', option: { label: '记录', referenceSheet: 'sheet' }, required: true },
  { type: 'text', key: 'text', option: { label: '文本' }, required: true },
  { type: 'number', key: 'number', option: { label: '数字' }, required: true },
  { type: 'select', key: 'select', option: { label: '选择', options: ['A', 'B'] }, required: true }
]);
```

**Record 类型（按钮触发支持）**：
- `type: 'record'` - 用于选择单条记录
- `option.referenceSheet` - 必须引用 Sheet 表单项的 key
- 当脚本通过按钮字段触发时，记录会自动填充为当前点击按钮的行
- 实现脚本既支持手动运行，也支持按钮快捷操作

**Important**: FormItem type values are different from field types:
- FormItem types: `sheet`, `field`, `view`, `record`, `text`, `number`, `select`
- Field types: `text`, `number`, `date`, `singleSelect`, `multipleSelect`, etc.
- When using `type: 'select'` in FormItem, it's a selector UI component, NOT a singleSelect field type
- Field type checking is done separately using `Base.isFieldOfType(field, 'singleSelect')`

### Output API
```typescript
Output.log('普通日志');
Output.info('提示信息');
Output.warn('警告信息');
Output.error('错误信息');
Output.markdown('# Markdown **formatted** text');
Output.table([{ name: 'John', age: 30 }, { name: 'Jane', age: 25 }]);
```

### Base API
```typescript
const sheets = Base.getSheets();
const sheet = Base.getActiveSheet();
const sheetById = Base.getSheet('sheetId');

// Type checking
if (Base.isFieldOfType(field, 'number')) {
  // Type-safe operations
}
```

### Network Request API
```typescript
// Basic GET request
const response = await fetch('https://api.example.com/data');
const data = await response.json();

// POST request with headers
const result = await fetch('https://api.example.com/create', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_TOKEN'
  },
  body: JSON.stringify({ key: 'value' })
});

// Error handling
try {
  const response = await fetch('https://api.example.com/data');
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const data = await response.json();
  Output.log('Data fetched successfully');
} catch (error) {
  Output.error(`Network request failed: ${error.message}`);
}
```

**Advanced Pattern - Signed API Requests**:
For APIs requiring signature (like Aliyun RAM), refer to `.skills/ai-script-generator/references/examples/network-requests/aliyun-ram-users.ts` for:
- HMAC-SHA1 signature generation using Web Crypto API
- URL encoding and parameter sorting
- Pagination handling
- Secure credential management

### Sheet API
```typescript
const fields = sheet.getFields();
const field = sheet.getField('fieldName');
const records = await sheet.getRecordsAsync({ pageSize: 500 });
await sheet.insertRecordsAsync([{ fields: { 'field': 'value' } }]);
await sheet.updateRecordsAsync([{ id: 'recId', fields: { 'field': 'newValue' } }]);
await sheet.deleteRecordsAsync(['recId1', 'recId2']);
```

**Important Notes**:
- **Field Identifiers**: In `insertRecordsAsync` and `updateRecordsAsync`, field identifiers can be either field IDs or field names. Use field names for simplicity.
- **insertField**: Use `sheet.insertField('fieldName', 'fieldType')` with separate parameters, NOT object form like `insertField({ name, type })`. There is no `FieldType` enum — pass string literals.
- **getField is NOT generic in script plugins**: write `sheet.getField('name')` then narrow with `Base.isFieldOfType(field, 'text')`. `sheet.getField<TextField>('name')` only compiles in a sidebar plugin's `service.ts`.
- **No addRecordsAsync or addFieldAsync**: These methods don't exist. Use `insertRecordsAsync` and `insertField` instead.
- **Field type literals**: `multipleSelect` (not `multiSelect`), `lastModifiedTime` (not `updatedTime`), `richText`, `telephone`, `geolocation`, `primaryDoc`, `autoNumber`.
- **`getRecordsAsync` filter** uses the `OpenApi.Filter` shape — `{ combination?: 'and' | 'or', conditions: [{ field, operator, value? }] }` with `operator` in `'equal' | 'notEqual' | 'greater' | 'greaterEqual' | 'less' | 'lessEqual' | 'contain' | 'notContain' | 'empty' | 'notEmpty'` and `value` as an **array**. Do NOT use the GridView filter shape (`conjunction` / `fieldId` / `'is'`).
- **Per-call limits (script/sidebar plugin)**: insert 1000, update 500, delete 500, `pageSize` 500.

## Troubleshooting

### Common Errors

**Error: "Service hook unregistered"**
- Cause: Using undocumented API methods
- Solution: Only use documented APIs from `references/api/` and  `../shared/references/api` directory

**Error: "xxx.addRecordsAsync is not a function"**
- Cause: Using non-existent API method
- Solution: Use `insertRecordsAsync` instead of `addRecordsAsync`

**Error: "xxx.addFieldAsync is not a function"**
- Cause: Using non-existent API method
- Solution: Use `insertField` instead of `addFieldAsync`

**Error: "xxx.insertField is not a function" with object parameter**
- Cause: Using wrong parameter format: `insertField({ name, type })`
- Solution: Use correct format: `insertField('fieldName', 'fieldType')`

**Error: "getField is not generic" / 编辑器在 `getField<TextField>(...)` 上报红**
- Cause: 脚本插件的 `getField` 声明是 `(idOrName: string) => Field | null`，没有泛型
- Solution: `const f = sheet.getField('name'); if (Base.isFieldOfType(f, 'text')) { ... }`

**Error: "the option '...' is invalid for field 'xxx'" 或 "the value '[object Object]' is invalid"**
- Cause: 单选/多选字段传了 `{ id }` / `{ name }` 对象，或选项不存在
- Solution: 脚本插件只能传字符串（选项 id 或选项名）；先用 `getOptions()` 确认选项存在，不存在先 `addOption()`

**Error: "operator 'is' is invalid condition for field 'xxx'"**
- Cause: 把 GridView 筛选的 `{ conjunction, fieldId, operator: 'is' }` 结构传给了 `getRecordsAsync({ filter })`
- Solution: 用 `{ combination: 'and', conditions: [{ field: '状态', operator: 'equal', value: ['x'] }] }`

**Error: "PageSize should be between 1 and 500."**
- Cause: `getRecordsAsync({ pageSize })` 超过 500
- Solution: `pageSize` 最大 500；需要更多数据用 `cursor` 分页

**Error: FormItem type confusion**
- Cause: Confusing FormItem types with field types (e.g., using `type: 'singleSelect'` in FormItem)
- Solution: Use `type: 'select'` for FormItem selector UI, check field types separately with `Base.isFieldOfType(field, 'singleSelect')`

**Error: "Field type mismatch"**
- Cause: Incorrect value type for field
- Solution: Match value type to field type (see Field-Specific Value Types)

**Error: "Batch size exceeded"**
- Cause: Exceeding the per-call limit (insert 1000 / update 500 / delete 500 / pageSize 500)
- Solution: Use batch processing with slice/splice

**Error: "Field not found"**
- Cause: Invalid field name or ID
- Solution: Verify field exists with `sheet.getField()` and check validity

### Validation Checklist

Before delivering generated code:
- [ ] All API calls match documentation exactly
- [ ] Field types checked with `Base.isFieldOfType()`
- [ ] Value types match field type requirements
- [ ] Batch operations within limits (insert ≤ 1000, update ≤ 500, delete ≤ 500, pageSize ≤ 500)
- [ ] Error handling with try-catch
- [ ] User feedback via Output methods
- [ ] No invented or undocumented methods
- [ ] Script name is concise (≤10 Chinese characters)
- [ ] Script description is detailed (≤100 Chinese characters)
- [ ] If script uses Record type, it supports button triggering
- [ ] Manifest.json only generated when user confirms script works and wants to publish
- [ ] **Manifest.base.scriptCode properly escaped with JSON.stringify()** - This is critical!
- [ ] If script supports button trigger, manifest.base.buttonTrigger set to true
- [ ] Manifest structure matches official examples in references/examples/manifest/ directory
- [ ] Manifest includes all required fields: extensionName, extensionType, classifications, schemaVersion, icon, i18nDesc, i18nName, i18nIntroduction, i18nVideo, i18nImage, i18nHelpLink, i18nDeveloper, manifest, privacyAgreement, agreement

## Best Practices

1. **Always validate input**: Check field types, data formats, and user permissions
2. **Use batch operations**: Process records in batches (insert ≤ 1000, update ≤ 500, delete ≤ 500, `pageSize` ≤ 500). The 100/500 REST OpenAPI limits do NOT apply to plugins.
3. **Provide feedback**: Use Output methods to inform user of progress
4. **Handle errors**: Wrap operations in try-catch blocks
5. **Type safety**: Use `Base.isFieldOfType()` before type-specific operations
6. **Avoid assumptions**: Don't assume data exists or is valid
7. **Document clearly**: Add comments explaining complex logic
8. **Test edge cases**: Handle null, undefined, empty values gracefully
9. **Support button triggers**: When appropriate, use `Input.formAsync` with Record type to enable button field triggering
10. **Generate manifest on demand**: Only create manifest.json when user confirms script works and wants to publish
11. **Name scripts clearly**: Provide concise names (≤10 characters) and detailed descriptions (≤100 characters)
12. **Reference official examples**: Check references/examples/manifest/ directory for proper manifest structure and buttonTrigger usage
9. **Support button triggers**: When appropriate, use Record type in Input.formAsync to enable button field triggering
10. **Separate script and manifest generation**: Generate script code first, then generate manifest.json only when user confirms it works and wants to publish
11. **Properly escape script code**: Always use JSON.stringify() to escape script code in manifest.base.scriptCode
12. **Confirm buttonTrigger setting**: Only set buttonTrigger to true when script is designed for button field execution and user confirms it should be visible in button configuration
13. **Secure network requests**: When using fetch API, ensure external endpoints support CORS, use secure authentication methods, collect credentials via Input API, and handle network errors gracefully
14. **Reference network examples**: For advanced network request patterns (signed APIs, pagination, etc.), refer to `.skills/ai-script-generator/references/examples/network-requests/aliyun-ram-users.ts` as a reference implementation
15. **Use correct API methods**: Only use documented APIs. Common mistakes:
    - ❌ Wrong: `addRecordsAsync`, `addFieldAsync`
    - ✅ Correct: `insertRecordsAsync`, `insertField`
    - ❌ Wrong: `insertField({ name, type })`
    - ✅ Correct: `insertField('fieldName', 'fieldType')`
    - ❌ Wrong: `numberField.getFormat()`, `field.getDescription()`, `sheet.getRecords()`, `sheet.insertRecordAsync()`
    - ✅ Correct: `numberField.getFormatter()`, `field.getDesc()`, `sheet.getRecordsAsync()`, `sheet.insertRecordsAsync()`
    - ❌ Wrong: `sheet.getField<TextField>('x')` in a script plugin
    - ✅ Correct: `Base.isFieldOfType(sheet.getField('x'), 'text')`
16. **Distinguish FormItem types from field types**: FormItem uses `type: 'select'` for selector UI, while field types include `singleSelect`, `multipleSelect`, etc.