---
name: ai-sidebar-plugin-generator
description: Generates production-ready sidebar plugins for AI Table (钉钉AI表格). Use when user asks to "create a sidebar plugin", "generate AI Table UI", "build plugin interface", or references specific UI features like "button triggers", "event listeners", "data display", "form interactions". Supports React-based UI with TypeScript, dual-page architecture (Service + UI), event monitoring, and real-time data interactions. Outputs complete code: service.ts, ui.tsx, script.tsx with proper API usage.
license: MIT
metadata:
  author: AI Table Team
  version: 1.0.0
  category: ui-development
  tags: [ai-table, sidebar-plugin, react, typescript, event-handling]
---

# AI Table Sidebar Plugin Generator

Generates production-ready sidebar plugins for AI Table (钉钉AI表格) with React-based UI, TypeScript support, and dual-page architecture. All generated plugins follow strict API compliance and include comprehensive error handling, event monitoring, and user interactions.

## Core Principles

1. **API Compliance**: Strictly follow AI Table API definitions in `./references/` and `../shared/references/api/` directory
2. **Dual-Page Architecture**: Separate Service page (Web Worker) for data operations and UI page (Sidebar iframe) for user interactions
3. **No Fabrication**: Never invent APIs or methods - only use documented interfaces
4. **Production Ready**: Include proper error handling, user feedback, event cleanup, and TypeScript type safety
5. **Event-Driven**: Support event listeners (button clicks, selection changes, record operations) with proper cleanup
6. **React-Based**: Use React for UI components with hooks and proper lifecycle management
7. **Permission Aware**: Check user permissions before performing operations

## Architecture Overview

Sidebar plugins use a dual-page architecture:

- **Service Page (service.ts)**: Runs in Web Worker, handles AI Table data model interactions via `DingdocsScript.base`
- **UI Page (ui.tsx)**: Runs in sidebar iframe, manages user interface with React components
- **Script Entry (script.tsx)**: Initializes the Service page using `initScript`

### Data Flow

```
User Action (ui.tsx)
    ↓
Dingdocs.script.run('commandName', params)
    ↓
Service Page (service.ts) - DingdocsScript.registerScript('commandName')
    ↓
AI Table API (DingdocsScript.base)
    ↓
Data Operations (CRUD, queries)
    ↓
Return Result to UI
    ↓
Update UI State
```

## Workflow

### Phase 1: Understand User Intent

Analyze user request to determine:
- **UI Components**: Data display, forms, buttons, selectors, tables, charts
- **Data Operations**: Read, create, update, delete records
- **Event Triggers**: Button clicks, selection changes, record modifications
- **User Interactions**: Form inputs, real-time updates, feedback messages
- **Complexity Level**: Simple display vs. complex business logic

**Ask clarifying questions if intent is ambiguous:**
- "What data should be displayed in the sidebar?"
- "Which sheet(s) should the plugin operate on?"
- "Should users be able to modify data from the UI?"
- "What events should trigger plugin actions?"
- "What visual elements are needed (forms, tables, charts)?"

### Phase 2: Consult API References

Before writing code, consult relevant API documentation:

**For Service Page (Data Operations):**
- `../shared/references/api/modules/Base 模块.md` - Base object methods
- `../shared/references/api/modules/Sheet 模块.md` - Sheet operations
- `../shared/references/api/modules/Field 模块.md` - Field operations
- `../shared/references/api/modules/Record 模块.md` - Record operations
- `../shared/references/api/modules/View 模块.md` - View operations

**For UI Page (Interactions):**
- `./references/AI表格边栏插件 开发指南.md` - Plugin development guide
- `./references/Event事件模块.md` - Event monitoring
- `./references/其他接口.md` - UI and helper APIs

**For Type Definitions:**
- `../shared/references/api/interface/API 类型定义.md` - Type structures
- `../shared/references/api/interface/字段类型结构.md` - Field value types

**Critical Rule**: Never use undocumented APIs. If a method is not in the documentation, it does not exist.

### Phase 3: Generate Service Page (service.ts)

#### Template Structure

```typescript
// 1. Define data operation functions
async function getSheetInfo() {
  const sheet = DingdocsScript.base.getActiveSheet();
  if (!sheet) {
    throw new Error('未找到激活的数据表');
  }
  
  const recordCount = (await sheet.getRecordsAsync({ pageSize: 1 })).total || 0;
  return {
    name: sheet.getName(),
    recordCount: recordCount
  };
}

// 2. Register script commands
DingdocsScript.registerScript('getSheetInfo', getSheetInfo);
```

#### Common Service Patterns

**Pattern 1: Read Data**
```typescript
async function getRecords(sheetId: string) {
  const sheet = DingdocsScript.base.getSheet(sheetId);
  if (!sheet) {
    throw new Error('数据表不存在');
  }
  
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
  
  return allRecords.map(record => ({
    id: record.getId(),
    fields: record.getCellValues()
  }));
}

DingdocsScript.registerScript('getRecords', getRecords);
```

**Pattern 2: Batch Update**
```typescript
async function batchUpdateRecords(sheetId: string, updates: Array<{id: string, fields: any}>) {
  const sheet = DingdocsScript.base.getSheet(sheetId);
  if (!sheet) {
    throw new Error('数据表不存在');
  }
  
  // updateRecordsAsync 在边栏插件下单次上限是 500 条
  const batchSize = 500;
  const results = [];
  
  for (let i = 0; i < updates.length; i += batchSize) {
    const batch = updates.slice(i, i + batchSize);
    const updated = await sheet.updateRecordsAsync(batch);
    results.push(...updated);
  }
  
  return results;
}

DingdocsScript.registerScript('batchUpdateRecords', batchUpdateRecords);
```

**Pattern 3: Create Record**
```typescript
async function createRecord(sheetId: string, fields: any) {
  const sheet = DingdocsScript.base.getSheet(sheetId);
  if (!sheet) {
    throw new Error('数据表不存在');
  }
  
  const result = await sheet.insertRecordsAsync([{ fields }]);
  return result[0];
}

DingdocsScript.registerScript('createRecord', createRecord);
```

**Pattern 4: Delete Record**
```typescript
async function deleteRecord(sheetId: string, recordId: string) {
  const sheet = DingdocsScript.base.getSheet(sheetId);
  if (!sheet) {
    throw new Error('数据表不存在');
  }
  
  await sheet.deleteRecordsAsync(recordId);
  return { success: true };
}

DingdocsScript.registerScript('deleteRecord', deleteRecord);
```

### Phase 4: Generate Script Entry (script.tsx)

#### Template Structure

```typescript
import React, { useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import { initScript } from 'dingtalk-docs-cool-app';

function App() {
  useEffect(() => {
    initScript({
      scriptUrl: new URL(`${process.env.PUBLIC_URL}/static/js/script.code.js`, window.location.href),
      onError: (e) => {
        console.error('Script initialization error:', e);
      }
    });
  }, []);
  
  return null;
}

// NOTE: public/script.html uses <div id="root_script">, NOT <div id="script">
const root = ReactDOM.createRoot(document.getElementById('root_script')!);
root.render(
  <React.StrictMode>
    <App/>
  </React.StrictMode>
);
```

### Phase 5: Generate UI Page (ui.tsx)

#### Template Structure

```typescript
import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { initView } from 'dingtalk-docs-cool-app';

function App() {
  const [ready, setReady] = useState(false);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    initView({
      onReady: () => {
        console.log('UI initialized successfully');
        setReady(true);  // Gate event listeners on this
        loadData();
      },
      onError: (e) => {
        console.error('UI initialization error:', e);
        setError('初始化失败');
      },
    });
  }, []);

  // Event listeners MUST be gated on `ready` to avoid white screen crashes
  // Dingdocs global is only available after initView onReady
  useEffect(() => {
    if (!ready) return;

    const off = Dingdocs.base.event.onSelectionChanged((selection: any) => {
      console.log('Selection changed:', selection);
    });

    return () => {
      off();
    };
  }, [ready]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await Dingdocs.script.run('getSheetInfo');
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>加载中...</div>;
  if (error) return <div>错误: {error}</div>;

  return (
    <div>
      <h1>边栏插件</h1>
      <button onClick={loadData}>刷新</button>
      {data && <pre>{JSON.stringify(data, null, 2)}</pre>}
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('ui')!);
root.render(
  <React.StrictMode>
    <App/>
  </React.StrictMode>
);
```

#### Common UI Patterns

**Pattern 1: Event Listener with Cleanup**
```typescript
useEffect(() => {
  const handleButtonClick = (event: any) => {
    console.log('Button clicked:', event);
    // Handle button click
  };

  const off = Dingdocs.base.event.onButtonFieldClicked(handleButtonClick);

  return () => {
    off(); // Clean up event listener
  };
}, []);
```

**Pattern 2: Selection Change Listener**
```typescript
useEffect(() => {
  const handleSelectionChange = (selection: any) => {
    console.log('Selection changed:', selection);
    // Update UI based on selection
  };

  const off = Dingdocs.base.event.onSelectionChanged(handleSelectionChange);

  return () => {
    off(); // Clean up event listener
  };
}, []);
```

**Pattern 3: Form with State Management**
```typescript
const [formData, setFormData] = useState({
  name: '',
  description: ''
});

const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
  setFormData({
    ...formData,
    [e.target.name]: e.target.value
  });
};

const handleSubmit = async () => {
  try {
    const result = await Dingdocs.script.run('createRecord', formData);
    console.log('Record created:', result);
    // Clear form or show success message
  } catch (err) {
    console.error('Create failed:', err);
  }
};

return (
  <form onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
    <input
      type="text"
      name="name"
      value={formData.name}
      onChange={handleChange}
      placeholder="名称"
    />
    <textarea
      name="description"
      value={formData.description}
      onChange={handleChange}
      placeholder="描述"
    />
    <button type="submit">提交</button>
  </form>
);
```

**Pattern 4: Data Table Display**
```typescript
const [records, setRecords] = useState<any[]>([]);

useEffect(() => {
  const loadRecords = async () => {
    try {
      const result = await Dingdocs.script.run('getRecords', sheetId);
      setRecords(result);
    } catch (err) {
      console.error('Load failed:', err);
    }
  };

  loadRecords();
}, [sheetId]);

return (
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>名称</th>
        <th>状态</th>
      </tr>
    </thead>
    <tbody>
      {records.map(record => (
        <tr key={record.id}>
          <td>{record.id}</td>
          <td>{record.fields['名称']}</td>
          <td>{record.fields['状态']}</td>
        </tr>
      ))}
    </tbody>
  </table>
);
```

**Pattern 5: Real-time Updates**
```typescript
useEffect(() => {
  const handleRecordModified = (event: any) => {
    console.log('Record modified:', event);
    // Reload data or update UI
    loadData();
  };

  const off = Dingdocs.base.event.onRecordModified(handleRecordModified);

  return () => {
    off();
  };
}, []);

// Auto-refresh interval
useEffect(() => {
  const interval = setInterval(() => {
    loadData();
  }, 30000); // Refresh every 30 seconds

  return () => {
    clearInterval(interval);
  };
}, []);
```

### Phase 6: Error Handling and User Feedback

#### Service Page Error Handling

```typescript
async function safeOperation(params: any) {
  try {
    // Validate inputs
    if (!params.sheetId) {
      throw new Error('缺少必要参数: sheetId');
    }

    // Perform operation
    const result = await performOperation(params);
    return { success: true, data: result };
  } catch (error) {
    console.error('Operation failed:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : '未知错误'
    };
  }
}

DingdocsScript.registerScript('safeOperation', safeOperation);
```

#### UI Page Error Handling

```typescript
const [error, setError] = useState<string | null>(null);
const [success, setSuccess] = useState<string | null>(null);

const handleAction = async () => {
  try {
    setError(null);
    setSuccess(null);
    
    const result = await Dingdocs.script.run('operationName', params);
    
    if (result.success) {
      setSuccess('操作成功');
      // Refresh data or update UI
    } else {
      setError(result.error || '操作失败');
    }
  } catch (err) {
    setError(err instanceof Error ? err.message : '操作失败');
  }
};

return (
  <div>
    {error && <div className="error">{error}</div>}
    {success && <div className="success">{success}</div>}
    <button onClick={handleAction}>执行操作</button>
  </div>
);
```

## Real-World Examples

Complete production-ready examples from the official plugin repository.

### Example 1: Button Trigger Plugin

**User Request**: "Create a plugin that listens to button field clicks and displays record data"

**Service Page (service.ts)**:
Reference: `./assets/examples/button-trigger-service.ts`

**UI Page (ui.tsx)**:
Reference: `./assets/examples/button-trigger-ui.tsx`

**Key Features**:
- Event listener for `onButtonFieldClicked`
- Displays record information when button is clicked
- Shows first 3 text fields of the record
- Includes timestamp of click event
- Proper cleanup of event listeners

### Example 2: Batch Field Modification Plugin

**User Request**: "Create a plugin to batch modify field types and hide/show fields in views"

**Service Page (service.ts)**:
Reference: `./assets/examples/batch-modify-service.ts`

**Key Features**:
- Batch modify field types with validation
- Batch hide/show fields in grid views
- Prevents hiding primary fields
- Detailed error reporting with field-level failures
- Returns comprehensive result information

### Example 3: CSV Import Plugin

**User Request**: "Create a plugin to import CSV data into AI Table"

**Key Features** (from plugin/examples/csv-import):
- CSV parsing with configurable delimiters
- Automatic field type inference
- Support for creating new sheets or appending to existing sheets
- Field mapping for append mode
- Batch import with progress tracking
- Error handling with ignore option
- Support for various field types (text, number, date, select, url, etc.)

### Example 4: Download Attachment Plugin

**Key Features** (from plugin/examples/download-attachment):
- Batch download attachments from records
- Progress tracking for large files
- Error handling for failed downloads
- Organizes downloaded files by record

### Example 5: Remove Duplicate Records Plugin

**Key Features** (from plugin/examples/remove-dup-records):
- Identifies duplicate records based on selected fields
- Provides preview before deletion
- Batch delete with confirmation
- Preserves original records when duplicates removed

### Example 6: Merge Tables Plugin

**Key Features** (from plugin/examples/merge-table):
- Combines data from multiple sheets
- Field mapping between sheets
- Conflict resolution strategies
- Preview of merge results

## Advanced UI Patterns

### Pattern 6: Form with Validation

```typescript
const [formData, setFormData] = useState({
  sheetId: '',
  fieldName: '',
  value: ''
});
const [errors, setErrors] = useState<Record<string, string>>({});

const validateForm = () => {
  const newErrors: Record<string, string> = {};
  
  if (!formData.sheetId) {
    newErrors.sheetId = '请选择数据表';
  }
  
  if (!formData.fieldName) {
    newErrors.fieldName = '请选择字段';
  }
  
  if (!formData.value) {
    newErrors.value = '请输入值';
  }
  
  setErrors(newErrors);
  return Object.keys(newErrors).length === 0;
};

const handleSubmit = async () => {
  if (!validateForm()) {
    return;
  }
  
  try {
    const result = await Dingdocs.script.run('updateField', formData);
    console.log('Update successful:', result);
    // Show success message
  } catch (err) {
    console.error('Update failed:', err);
    // Show error message
  }
};

return (
  <form onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
    <div>
      <label>数据表:</label>
      <select 
        value={formData.sheetId}
        onChange={(e) => setFormData({...formData, sheetId: e.target.value})}
      >
        <option value="">请选择</option>
        {sheets.map(sheet => (
          <option key={sheet.id} value={sheet.id}>{sheet.name}</option>
        ))}
      </select>
      {errors.sheetId && <div className="error">{errors.sheetId}</div>}
    </div>
    
    <div>
      <label>字段:</label>
      <select 
        value={formData.fieldName}
        onChange={(e) => setFormData({...formData, fieldName: e.target.value})}
      >
        <option value="">请选择</option>
        {fields.map(field => (
          <option key={field.id} value={field.id}>{field.name}</option>
        ))}
      </select>
      {errors.fieldName && <div className="error">{errors.fieldName}</div>}
    </div>
    
    <div>
      <label>值:</label>
      <input
        type="text"
        value={formData.value}
        onChange={(e) => setFormData({...formData, value: e.target.value})}
      />
      {errors.value && <div className="error">{errors.value}</div>}
    </div>
    
    <button type="submit">提交</button>
  </form>
);
```

### Pattern 7: Real-time Data Table with Selection

```typescript
const [records, setRecords] = useState<any[]>([]);
const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
const [loading, setLoading] = useState(false);

const loadRecords = async () => {
  setLoading(true);
  try {
    const result = await Dingdocs.script.run('getRecords', { sheetId });
    setRecords(result);
  } catch (err) {
    console.error('Load failed:', err);
  } finally {
    setLoading(false);
  }
};

const toggleSelection = (id: string) => {
  const newSelection = new Set(selectedIds);
  if (newSelection.has(id)) {
    newSelection.delete(id);
  } else {
    newSelection.add(id);
  }
  setSelectedIds(newSelection);
};

const batchDeleteSelected = async () => {
  if (selectedIds.size === 0) return;
  
  try {
    const result = await Dingdocs.script.run('batchDeleteRecords', {
      sheetId,
      recordIds: Array.from(selectedIds)
    });
    console.log('Delete successful:', result);
    loadRecords(); // Reload after deletion
    setSelectedIds(new Set());
  } catch (err) {
    console.error('Delete failed:', err);
  }
};

return (
  <div>
    <button onClick={loadRecords} disabled={loading}>
      {loading ? '加载中...' : '刷新'}
    </button>
    
    {selectedIds.size > 0 && (
      <button onClick={batchDeleteSelected}>
        删除选中 ({selectedIds.size})
      </button>
    )}
    
    <table>
      <thead>
        <tr>
          <th><input 
            type="checkbox" 
            checked={records.length > 0 && selectedIds.size === records.length}
            onChange={(e) => {
              if (e.target.checked) {
                setSelectedIds(new Set(records.map(r => r.id)));
              } else {
                setSelectedIds(new Set());
              }
            }}
          /></th>
          <th>ID</th>
          <th>名称</th>
          <th>状态</th>
        </tr>
      </thead>
      <tbody>
        {records.map(record => (
          <tr key={record.id}>
            <td>
              <input 
                type="checkbox"
                checked={selectedIds.has(record.id)}
                onChange={() => toggleSelection(record.id)}
              />
            </td>
            <td>{record.id}</td>
            <td>{record.fields['名称']}</td>
            <td>{record.fields['状态']}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);
```

### Pattern 8: Progress Indicator for Long Operations

```typescript
const [progress, setProgress] = useState<{ current: number; total: number; message: string }>({
  current: 0,
  total: 0,
  message: ''
});
const [processing, setProcessing] = useState(false);

const processBatch = async (items: any[]) => {
  setProcessing(true);
  setProgress({ current: 0, total: items.length, message: '开始处理...' });
  
  // 这里的 50 是 UI 侧的进度分片粒度（控制进度条刷新频率），不是记录 API 上限。
  // Service 层真正写入时，insertRecordsAsync 上限 1000、updateRecordsAsync / deleteRecordsAsync 上限 500。
  const batchSize = 50;
  const results = [];
  
  for (let i = 0; i < items.length; i += batchSize) {
    const batch = items.slice(i, i + batchSize);
    
    try {
      const result = await Dingdocs.script.run('processBatch', batch);
      results.push(...result);
      setProgress({
        current: results.length,
        total: items.length,
        message: `正在处理 ${results.length}/${items.length}...`
      });
    } catch (err) {
      console.error(`Batch ${i}-${i + batchSize} failed:`, err);
    }
  }
  
  setProgress({
    current: results.length,
    total: items.length,
    message: '处理完成'
  });
  setProcessing(false);
  
  return results;
};

return (
  <div>
    {processing && (
      <div>
        <div>进度: {progress.current} / {progress.total}</div>
        <div>{progress.message}</div>
        <div style={{ width: '100%', height: '10px', backgroundColor: '#f0f0f0', borderRadius: '5px' }}>
          <div 
            style={{ 
              width: `${(progress.current / progress.total) * 100}%`, 
              height: '100%', 
              backgroundColor: '#1890ff',
              borderRadius: '5px',
              transition: 'width 0.3s ease'
            }}
          />
        </div>
      </div>
    )}
  </div>
);
```

### Pattern 9: Responsive Layout with Tabs

```typescript
const [activeTab, setActiveTab] = useState<'data' | 'settings' | 'help'>('data');

return (
  <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
    <div style={{ display: 'flex', borderBottom: '1px solid #d9d9d9' }}>
      <button
        onClick={() => setActiveTab('data')}
        style={{
          padding: '12px 20px',
          border: 'none',
          borderBottom: activeTab === 'data' ? '2px solid #1890ff' : 'none',
          backgroundColor: activeTab === 'data' ? '#fff' : 'transparent',
          cursor: 'pointer'
        }}
      >
        数据
      </button>
      <button
        onClick={() => setActiveTab('settings')}
        style={{
          padding: '12px 20px',
          border: 'none',
          borderBottom: activeTab === 'settings' ? '2px solid #1890ff' : 'none',
          backgroundColor: activeTab === 'settings' ? '#fff' : 'transparent',
          cursor: 'pointer'
        }}
      >
        设置
      </button>
      <button
        onClick={() => setActiveTab('help')}
        style={{
          padding: '12px 20px',
          border: 'none',
          borderBottom: activeTab === 'help' ? '2px solid #1890ff' : 'none',
          backgroundColor: activeTab === 'help' ? '#fff' : 'transparent',
          cursor: 'pointer'
        }}
      >
        帮助
      </button>
    </div>
    
    <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
      {activeTab === 'data' && <DataView />}
      {activeTab === 'settings' && <SettingsView />}
      {activeTab === 'help' && <HelpView />}
    </div>
  </div>
);
```

### Pattern 10: Multi-Language Support

```typescript
const [locale, setLocale] = useState<string>('zh-CN');
const [ready, setReady] = useState(false);

const translations = {
  'zh-CN': {
    title: '标题',
    submit: '提交',
    loading: '加载中...',
    success: '成功',
    error: '错误'
  },
  'en-US': {
    title: 'Title',
    submit: 'Submit',
    loading: 'Loading...',
    success: 'Success',
    error: 'Error'
  }
};

useEffect(() => {
  const init = async () => {
    initView({
      onReady: async () => {
        const currentLocale = await Dingdocs.base.host.getLocale();
        setLocale(currentLocale);
        setReady(true);
      },
      onError: (e) => console.error(e)
    });
  };
  
  init();
}, []);

const t = (key: keyof typeof translations['zh-CN']) => {
  return translations[locale as keyof typeof translations]?.[key] || key;
};

if (!ready) {
  return <div>{t('loading')}</div>;
}

return (
  <div>
    <h1>{t('title')}</h1>
    <button onClick={handleSubmit}>{t('submit')}</button>
  </div>
);
```

## Working with Examples

The Skill provides real-world examples in the `./assets/examples/` directory. These examples are from the official plugin repository and demonstrate production-ready patterns.

### Available Examples

1. **button-trigger-service.ts / button-trigger-ui.tsx** - Event listener for button field clicks
2. **batch-modify-service.ts** - Batch field type modification and view control
3. **csv-import** (from plugin/examples) - CSV data import with field type inference
4. **download-attachment** (from plugin/examples) - Batch attachment download
5. **remove-dup-records** (from plugin/examples) - Duplicate record detection and removal
6. **merge-table** (from plugin/examples) - Merge multiple sheets

### How to Use Examples

**For Reference:**
```typescript
// Reference the example code to understand patterns
// Example: ./assets/examples/button-trigger-service.ts
```

**For Learning:**
- Study the service page to understand data operations
- Study the UI page to understand React patterns
- Examine error handling and user feedback
- Learn event listener cleanup patterns

**For Adaptation:**
- Copy relevant code sections to your project
- Modify to fit your specific requirements
- Adapt the patterns to your use case
- Maintain the same structure and best practices

### Example-Based Learning Path

**Beginner:** Start with `button-trigger` to understand:
- Basic dual-page architecture
- Event listener setup and cleanup
- Simple data fetching
- State management in React

**Intermediate:** Study `batch-modify` to learn:
- Complex data operations
- Batch processing patterns
- Error handling with detailed feedback
- Field and view manipulation

**Advanced:** Explore `csv-import` to master:
- Data parsing and validation
- Field type inference
- Complex data transformation
- Large-scale data handling
- Progress tracking

## Common Operations Reference

### Service Page APIs

**Base API**:
```typescript
const base = DingdocsScript.base;
const sheet = base.getActiveSheet();
const sheets = base.getSheets();
```

**Sheet API**:
```typescript
const fields = sheet.getFields();
const field = sheet.getField('fieldName');
const records = await sheet.getRecordsAsync({ pageSize: 500 }); // 上限 500
await sheet.insertRecordsAsync([{ fields: { 'field': 'value' } }]);
await sheet.updateRecordsAsync([{ id: 'recId', fields: { 'field': 'newValue' } }]);
await sheet.deleteRecordsAsync(['recId1', 'recId2']);
```

**Field API**:
```typescript
if (DingdocsScript.base.isFieldOfType(field, 'number')) {
  const value = await field.getValueAsync(recordId);
  await field.setValueAsync(recordId, newValue);
}
```

### UI Page APIs

**Initialization**:
```typescript
initView({
  onReady: () => { /* Ready */ },
  onError: (e) => { /* Error */ },
});
```

**Script Execution**:
```typescript
const result = await Dingdocs.script.run('commandName', params);
```

**Event Listeners**:
```typescript
// Button click
const off = Dingdocs.base.event.onButtonFieldClicked((event) => {
  console.log('Button clicked:', event);
});

// Selection change
const off2 = Dingdocs.base.event.onSelectionChanged((selection) => {
  console.log('Selection changed:', selection);
});

// Record operations
const off3 = Dingdocs.base.event.onRecordInserted((event) => {
  console.log('Record inserted:', event);
});

// Cleanup
return () => {
  off();
  off2();
  off3();
};
```

**UI Helper**:
```typescript
// Toast messages (if available)
await Dingdocs.base.host.configPermission(...); // For authentication
```

## Troubleshooting

### Common Errors

**Error: "Script service unregistered"**
- Cause: Using incorrect script command name or service not initialized
- Solution: Ensure command name matches between `registerScript` and `script.run`

**Error: "Event listener not working"**
- Cause: Event listener not properly registered or cleaned up
- Solution: Use `useEffect` with cleanup function, verify event name is correct

**Error: "Permission denied"**
- Cause: User doesn't have required permissions
- Solution: Check permissions using `base.getPermissionAsync()` or display error message

**Error: "React component not rendering"**
- Cause: Missing or incorrect DOM element
- Solution: Ensure `document.getElementById('ui')` exists in the HTML template

**Error: "Type mismatch"**
- Cause: Incorrect TypeScript types
- Solution: Use proper type definitions from `../shared/references/api/interface/`

### Common Pitfalls (from real-world debugging)

**Pitfall 1: TextField is NOT a top-level export from dingtalk-docs-cool-app (TS2304/TS2305)**

`TextField` is exported under the `BaseApi` namespace, not as a direct named export.

❌ Wrong:
```typescript
import type { TextField } from 'dingtalk-docs-cool-app';  // TS2305: no exported member
const field = sheet.getField<TextField>(fieldName);
```

✅ Correct:
```typescript
import { BaseApi } from 'dingtalk-docs-cool-app';
const field = sheet.getField<BaseApi.TextField>(fieldName);
```

**Pitfall 2: isFieldOfType does NOT expose TextField-specific methods (TS2339)**

`isFieldOfType(field, 'text')` narrows to `Field<'text'>`, which does NOT have `getValueAsync`/`setValueAsync`. Those methods are on `TextField` (extends `Field<'text'>`).

❌ Wrong:
```typescript
const field = sheet.getField(fieldName);
if (Base.isFieldOfType(field, 'text')) {
  const value = await field.getValueAsync(recordId);  // TS2339: Property 'getValueAsync' does not exist
}
```

✅ Correct:
```typescript
// For type checks only (no TextField methods needed):
if (field.getType() === 'text') { ... }

// For accessing TextField-specific methods like getValueAsync:
const field = sheet.getField<BaseApi.TextField>(fieldName);
const value = await field.getValueAsync(recordId);
```

**Pitfall 3: getRecordsAsync cursor is `string | undefined` (TS2322)**

The `cursor` field in `GetRecordsResult` is `string | undefined`, not `string`. Declaring the loop variable as `string` causes a type error on assignment.

❌ Wrong:
```typescript
let cursor = '';  // type inferred as string
cursor = result.cursor;  // TS2322: Type 'string | undefined' is not assignable to type 'string'
```

✅ Correct:
```typescript
let cursor: string | undefined = '';
cursor = result.cursor;
```

**Pitfall 4: Event listeners must NOT be registered before initView onReady (causes white screen)**

`Dingdocs.base.event.*` relies on the `Dingdocs` global object injected by the AI Table runtime. If you register event listeners in a `useEffect` that runs before `initView` completes, `Dingdocs` may be undefined, causing a JS crash that renders the entire sidebar blank (white screen with no content).

❌ Wrong:
```typescript
useEffect(() => {
  initView({ onReady: () => loadData() });
}, []);

useEffect(() => {
  // Dingdocs may be undefined here → JS crash → blank page
  const off = Dingdocs.base.event.onSelectionChanged(handler);
  return () => off();
}, []);
```

✅ Correct — gate event listeners on a `ready` state:
```typescript
const [ready, setReady] = useState(false);

useEffect(() => {
  initView({
    onReady: () => {
      setReady(true);  // Only now register events
      loadData();
    },
  });
}, []);

useEffect(() => {
  if (!ready) return;  // Wait for initView to complete
  const off = Dingdocs.base.event.onSelectionChanged(handler);
  return () => off();
}, [ready]);
```

**Pitfall 5: script.html template uses `id="root_script"`, NOT `id="script"`**

The addon-demo template's `public/script.html` has `<div id="root_script">`. If `script.tsx` uses `getElementById('script')`, React fails to mount silently, `initScript` is never called, and all `Dingdocs.script.run()` calls fail with errors like "获取数据表信息失败".

❌ Wrong:
```typescript
const root = ReactDOM.createRoot(document.getElementById('script')!);
```

✅ Correct:
```typescript
const root = ReactDOM.createRoot(document.getElementById('root_script')!);
```

Similarly, `public/ui.html` uses `<div id="ui">`, so `ui.tsx` must use `getElementById('ui')`.

**Pitfall 6: Plugin URLs are `ui.html` + `script.html`, NOT `sidebar.html`**

The addon-demo template generates `ui.html` and `script.html` as the two HTML entry points. When configuring a custom plugin in AI Table, the correct addresses are:

- **交互页面地址 (UI)**: `http://localhost:3000/ui.html`
- **脚本服务地址 (Script)**: `http://localhost:3000/script.html`

The development guide mentions `sidebar.html` in some places, but the actual addon-demo template does not generate that file.

### Validation Checklist

Before delivering generated code:
- [ ] All API calls match documentation exactly
- [ ] Service page uses `DingdocsScript.registerScript` for all commands
- [ ] UI page uses `Dingdocs.script.run` to call service commands
- [ ] Event listeners are properly registered and cleaned up
- [ ] Event listeners are gated on `ready` state (only after `initView` onReady)
- [ ] `script.tsx` uses `getElementById('root_script')` (NOT `'script'`)
- [ ] `ui.tsx` uses `getElementById('ui')`
- [ ] TextField imported via `BaseApi.TextField` (NOT direct `TextField` import)
- [ ] `getRecordsAsync` cursor variable typed as `string | undefined`
- [ ] Error handling in both service and UI pages
- [ ] TypeScript types are correct
- [ ] React hooks are used properly (no side effects in render)
- [ ] No memory leaks (cleanup functions in useEffect)
- [ ] User feedback for loading and error states
- [ ] No invented or undocumented APIs

## Best Practices

1. **Separate Concerns**: Keep data operations in service.ts, UI logic in ui.tsx
2. **Type Safety**: Use TypeScript types from API documentation
3. **Error Boundaries**: Handle errors gracefully with user feedback
4. **Loading States**: Show loading indicators during async operations
5. **Event Cleanup**: Always clean up event listeners in useEffect cleanup
6. **Permission Checks**: Verify user has required permissions before operations
7. **Batch Operations**: Process records in batches for large datasets
8. **User Feedback**: Provide clear feedback for all user actions
9. **Code Organization**: Keep components focused and reusable
10. **Performance**: Use React.memo, useMemo, useCallback for optimization
11. **Security**: Never expose sensitive data or credentials
12. **Testing**: Test edge cases (empty data, errors, null values)
13. **Documentation**: Add comments for complex logic
14. **Accessibility**: Ensure UI is accessible (aria labels, keyboard navigation)
15. **Responsive Design**: Make UI work on different screen sizes

## Publishing Guidance

When users mention publishing, provide guidance from:
- `./references/AI 表格插件 - 企业内插件发布指南.md` - Enterprise plugin publishing
- `./references/ISV接入AI表格开放API.md` - ISV integration
- `./references/其他接口.md` - Authentication and configuration

Key points:
- Configure plugin authentication with `Dingdocs.base.host.configPermission`
- Set up cool app in DingTalk developer console
- Configure user interface address and service address
- Test plugin before publishing
- Get corpId from URL parameters for multi-organization support