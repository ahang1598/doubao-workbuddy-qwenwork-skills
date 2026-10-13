# Sheet 模块

`Sheet`即数据表，它负责维护数据与数据之间的联系，接口提供了操作数据表的方法，包括基本信息管理、字段管理、视图管理以及记录操作等功能

通过 `Base` 获取到 `Sheet` 之后，就可以调用 `Sheet` 中的 API，可以通过 `base.getActiveSheet` 方法来获取当前选中的数据表实例：

```typescript
const sheet = DingdocsScript.base.getActiveSheet();
const sheet = DingdocsScript.base.getSheet('数据表1');
```
```typescript
const sheet = Base.getActiveSheet();
const sheet = Base.getSheet('数据表1');
```
> 文中未声明的类型定义，请至[请至钉钉文档查看附件《AI表格JSAPI 类型描述》](../modules/Sheet%20模块.md)中进行查询

## 基本信息方法

### getId

获取当前数据表ID。

```typescript
getId(): string
```

**返回值**

*   `string` - 数据表ID
    

**示例**

```typescript
const sheetId = sheet.getId();
console.log(`当前数据表ID: ${sheetId}`);

```
```typescript
const sheetId = sheet.getId();
Output.log(`当前数据表ID: ${sheetId}`);

```

### getName

获取当前数据表名称。

```typescript
getName(): string

```

**返回值**

*   `string` - 数据表名称
    

**示例**

```typescript
const sheetName = sheet.getName();
console.log(`当前数据表名称: ${sheetName}`);

```
```typescript
const sheetName = sheet.getName();
console.log(`当前数据表名称: ${sheetName}`);

```

### setName

设置当前数据表名称。

```typescript
setName(name: string): Sheet

```

**参数**

*   `name`: `string` - 数据表名称
    

**返回值**

*   `Sheet` - Sheet对象本身，支持链式调用
    

**示例**

```typescript
sheet.setName('销售记录');
// 链式调用
sheet.setName('客户信息').getFields();

```

**注意事项**

*   数据表名称长度不能超过100个字符
    
*   不能包含以下特殊字符: `/\?*[ ]:`
    
*   不能与已有数据表同名
    

### getDesc

获取数据表描述。

```typescript
getDesc(): string | undefined

```

**返回值**

*   `string | undefined` - 数据表描述文案，没有描述时默认返回undefined
    

**示例**

```typescript
const description = sheet.getDesc();
if (description) {
  console.log(`数据表描述: ${description}`);
} else {
  console.log('该数据表暂无描述');
}

```
```typescript
const description = sheet.getDesc();
if (description) {
  Output.log(`数据表描述: ${description}`);
} else {
  Output.log('该数据表暂无描述');
}

```

### setDesc

设置当前数据表描述。

```typescript
setDesc(desc: string): Sheet

```

**参数**

*   `desc`: `string` - 数据表描述文案
    

**返回值**

*   `Sheet` - Sheet对象本身，支持链式调用
    

**示例**

```typescript
sheet.setDesc('本表用于记录公司客户的基本信息和联系方式');

```

## 字段管理方法

参考[《字段数据结构》](../interface/字段类型结构.md)了解如何读写字段配置。

### isFieldExist

判断当前数据表中指定ID的字段是否存在。

```typescript
isFieldExist(fieldId: string): boolean

```

**参数**

*   `fieldId`: `string` - 字段ID
    

**返回值**

*   `boolean` - 是否存在
    

**示例**

```typescript
if (sheet.isFieldExist('fld123456')) {
  console.log('字段存在，可以进行操作');
} else {
  console.log('字段不存在，请检查字段ID');
}

```
```typescript
if (sheet.isFieldExist('fld123456')) {
  Output.log('字段存在，可以进行操作');
} else {
  Output.log('字段不存在，请检查字段ID');
}

```

### getFields

获取当前数据表中所有字段列表。

```typescript
getFields(): Field[]

```

**返回值**

*   [`Field[]`](../modules/Field%20模块.md) - 字段列表
    

**示例**

```typescript
const fields = sheet.getFields();
console.log(`数据表共有 ${fields.length} 个字段`);
fields.forEach(field => {
  console.log(`- ${field.getName()}: ${field.getType()}`);
});

```
```typescript
const fields = sheet.getFields();
Output.log(`数据表共有 ${fields.length} 个字段`);
fields.forEach(field => {
  Output.log(`- ${field.getName()}: ${field.getType()}`);
});

```

### getField

根据字段ID或字段名称获取指定字段。

```typescript
getField<T extends Field = Field>(idOrName: string): T | null
```

**参数**

*   `idOrName`: `string` - 字段ID或字段名称
    

**返回值**

*   [`Field | null`](../modules/Field%20模块.md) - 字段对象，若当前未找到符合条件的字段，则返回null
    

**示例**

*   边栏插件
    

```typescript
// 通过字段ID获取字段
const fieldById = sheet.getField('fld123456');

// 通过字段名称获取字段
const fieldByName = sheet.getField('客户姓名');
if (fieldByName) {
  console.log(`字段类型: ${fieldByName.getType()}`);
} else {
  console.log('未找到指定字段');
}

```

建议传入 `Field` 类型(例如示例中的 `<AttachmentField>`)，来获得更好的语法提示

```typescript
// getAttachmentUrls是附件字段独有的方法
const field = sheet.getField<AttachmentField>(idOrName);
const urls = field.getAttachmentUrls('recordId');
```

*   脚本插件
    

```typescript
// 通过字段ID获取字段
const fieldById = sheet.getField('fld123456');

// 通过字段名称获取字段
const fieldByName = sheet.getField('客户姓名');
if (fieldByName) {
  Output.log(`字段类型: ${fieldByName.getType()}`);
} else {
  Output.log('未找到指定字段');
}

```

建议使用`isFieldOfType` API判断字段类型，以获得更好的语法提示

```typescript
// addOption是单选/多选字段独有的方法
if (Base.isFieldOfType(field, 'singleSelect')) {
    field.addOption('新选项')
}
```

### getFieldsByType

获取当前数据表中所有指定类型的字段列表。

```typescript
getFieldsByType: <T extends FieldType>(type: T) => Array<Field<T>>

```

**参数**

*   `type`: [`FieldType`](../interface/API%20类型定义.md) - 指定字段类型
    

**返回值**

*   [`Field<T>[]`](../modules/Field%20模块.md) - 指定类型的字段列表
    

**示例**

```typescript
const fields = sheet.getFieldsByType('number');
console.log(`数据表共有 ${fields.length} 个数字字段`);

```
```typescript
const fields = sheet.getFieldsByType('number');
Output.log(`数据表共有 ${fields.length} 个数字字段`);

```

### insertField

插入字段。

```typescript
insertField: (name: string, type: FieldType, property?: FieldProperty) => Field

```

**参数**

*   `name`: `string` - 字段名称
    
*   `type`: [`FieldType`](../interface/API%20类型定义.md) - 字段类型
    
*   `property`: [`FieldProperty`](../interface/API%20类型定义.md) - 字段属性
    

根据字段类型不同，支持传入的字段属性结构也不同，具体可以参考[《字段数据结构》](../interface/字段类型结构.md)

**返回值**

*   [`Field`](../modules/Field%20模块.md) - 插入的字段对象
    

**示例**

```typescript
// 插入文本字段
const textField = sheet.insertField('备注', 'text');
```

### updateField

更新指定字段配置。

如果要修改字段类型，请调用【updateFieldAsync】

```typescript
updateField: (field: FieldToUpdateWithoutType) => Field

```

**参数**

*   `field`: [`FieldToUpdateWithoutType`](../interface/API%20类型定义.md) - 字段配置
    

根据字段类型不同，支持传入的字段属性结构也不同，具体可以参考[《字段数据结构》](../interface/字段类型结构.md)

**返回值**

*   [`Field`](../modules/Field%20模块.md) - 更新后的字段对象
    

### updateFieldAsync

更新指定字段配置，包括【字段类型】

```typescript
updateFieldAsync: (id: string, field: FieldToUpdate) => Promise<Field>

```

**参数**

*   `id`: `string` - 字段ID
    
*   `field`: [`FieldToUpdate`](../interface/API%20类型定义.md) - 字段配置
    

根据字段类型不同，支持传入的字段属性结构也不同，具体可以参考[《字段数据结构》](../interface/字段类型结构.md)

**返回值**

*   [`Promise<Field>`](../modules/Field%20模块.md) - 更新后的字段对象
    

### deleteField

根据字段ID或字段名称删除指定字段。

```typescript
deleteField: (idOrName: string) => Sheet
```

**参数**

*   `idOrName`: `string` - 字段ID或字段名称
    

**返回值**

*   `Sheet` - Sheet对象本身，支持链式调用
    

**示例**

```typescript
// 通过字段ID删除字段
sheet.deleteField('fld123456');

// 通过字段名称删除字段
sheet.deleteField('临时备注');

// 链式调用
sheet.deleteField('不需要的字段').setName('更新后的表名');

```

**注意事项**

*   不能删除主键字段
    
*   不能删除表中的最后一个字段
    

## 视图管理方法

### getViews

获取当前数据表的所有视图列表。

```typescript
getViews(): View[]
```

**返回值**

*   [`View[]`](../modules/View%20模块.md) - 视图列表
    

**示例**

```typescript
const views = sheet.getViews();
console.log(`数据表共有 ${views.length} 个视图`);

```
```typescript
const views = sheet.getViews();
console.log(`数据表共有 ${views.length} 个视图`);

```

### getView

根据视图ID或视图名称获取指定视图。

```typescript
getView(idOrName: string): View | null

```

**参数**

*   `id`: `string` - 指定视图的ID或视图名
    

**返回值**

*   [`View | null`](../modules/View%20模块.md) - 指定的视图对象，未找到视图时返回null
    

```typescript
const view = sheet.getView('表格视图');
```

### getActiveView

获取指定数据表中激活的视图。

```typescript
getActiveView(): View | null

```

**返回值**

*   [`View | null`](../modules/View%20模块.md) - 当前激活的视图对象，未激活对应数据表视图时返回null
    

```typescript
const view = sheet.getActiveView('表格视图');
```

### insertView

插入视图。

```typescript
insertView: (view: ViewToInsert) => View;

```

**参数**

*   `view`: [`ViewToInsert`](../interface/API%20类型定义.md) - 视图配置
    

**返回值**

*   [`View`](../modules/View%20模块.md) - 插入的视图对象
    

```typescript
const view = sheet.insertView({
  name: '新建的表格视图',
  type: 'Grid',
  desc: '由插件创建的表格视图',
});
```

### updateView

根据视图ID更新指定视图。

```typescript
updateView: (id: string, view: ViewToUpdate) => View;

```

**参数**

*   `view`: [`ViewToUpdate`](../interface/API%20类型定义.md) - 视图配置
    

**返回值**

*   [`View`](../modules/View%20模块.md) - 插入的视图对象
    

```typescript
const view = sheet.updateView('viewIdxx1', {
  name: '新视图名称',
  desc: '新的视图描述',
});
```

### deleteView

根据视图ID更新指定视图。

```typescript
deleteView: (idOrName: string) => Sheet;

```

**参数**

*   `idOrName`: `string` - 视图ID或视图名称
    

**返回值**

*   `Sheet` - Sheet对象本身
    

```typescript
const view = sheet.deleteView('视图名称');
```

## 记录操作方法

参考 [《字段数据结构》](../interface/字段类型结构.md) 了解如何读写记录单元格值。

### getRecordAsync

获取指定ID的单条记录。

```typescript
getRecordAsync: (recordId: string) => Promise<Record | null>
```

**参数**

*   `recordId`: `string` - 记录ID
    

**返回值**

*   [`Promise<Record | null>`](../modules/Record%20模块.md) - 记录对象，如果记录不存在则返回null
    

根据字段类型不同，收到的字段值结构也不同，具体可以参考[《字段数据结构》](../interface/字段类型结构.md)

**示例**

```typescript
// 获取指定ID的记录
const record = await sheet.getRecordAsync('rec123456');
if (record) {
  console.log(`记录标题: ${record.getCellValue('标题')}`);
  console.log(`记录创建时间: ${record.getCellValue('创建时间')}`);
} else {
  console.log('未找到指定记录');
}

```
```typescript
// 获取指定ID的记录
const record = await sheet.getRecordAsync('rec123456');
if (record) {
  Output.log(`记录标题: ${record.getCellValue('标题')}`);
  Output.log(`记录创建时间: ${record.getCellValue('创建时间')}`);
} else {
  Output.log('未找到指定记录');
}

```

### getRecordsAsync

分页加载数据表中的记录。

```typescript
getRecordsAsync: (options?: GetRecordsOptions) => Promise<GetRecordsResult>

```

**参数**

*   `options`: [`GetRecordsOptions`](../interface/API%20类型定义.md) 分页加载记录配置
    

**返回值**

*   [`Promise<GetRecordsResult>`](../interface/API%20类型定义.md) - 返回结果
    

根据字段类型不同，收到的字段值结构也不同，具体可以参考[《字段数据结构》](../interface/字段类型结构.md)

**示例**

```typescript
// 基本使用 - 使用选项对象
const result = await sheet.getRecordsAsync({ 
  pageSize: 50 
});
console.log(`获取了 ${result.records.length} 条记录`);
result.records.forEach(record => {
  console.log(`- ${record.getCellValue('标题')}`);
});


// 分页加载所有记录
async function loadAllRecords(sheet) {
  const allRecords = [];

  let hasMore = true;
  let cursor = '';
  
  while (hasMore) {
    const result = await sheet.getRecordsAsync({
      pageSize: 500,
      cursor: cursor
    });
    
    allRecords.push(...result.records);
    hasMore = result.hasMore;
    cursor = result.cursor;
    
    console.log(`已加载 ${allRecords.length} 条记录...`);
  }
  
  return allRecords;
}

```
```typescript
// 基本使用
const result = await sheet.getRecordsAsync({
  pageSize: 50,
});
Output.log(`获取了 ${result.records.length} 条记录`);
result.records.forEach(record => {
  console.log(`- ${record.getCellValue('标题')}`);
});


// 分页加载所有记录
async function loadAllRecords(sheet) {
  const allRecords = [];

  let hasMore = true;
  let cursor = '';
  
  while (hasMore) {
    const result = await sheet.getRecordsAsync({
      pageSize: 500,
      cursor: cursor
    });
    
    allRecords.push(...result.records);
    hasMore = result.hasMore;
    cursor = result.cursor;
    
    Output.log(`已加载 ${allRecords.length} 条记录...`);
  }
  
  return allRecords;
}

```

**注意事项**

*   `pageSize` 不传时，脚本插件/边栏插件默认为 500 条；可传入的范围是 1~500，超过 500 会报 `PageSize should be between 1 and 500`
    
*   （REST OpenAPI 通道的上限是 100，不适用于插件场景，不要把两者混淆）
    
*   通过多次调用并使用游标可以加载所有符合条件的记录
    
*   对于性能考虑，建议适当设置页面大小，避免一次加载过多数据
    
*   返回的记录已经过权限过滤，只包含当前用户有权限查看的记录
    

### insertRecordsAsync

批量插入行记录。

```typescript
insertRecordsAsync: (records: RecordToInsert[]) => Promise<Record[]>

```

**参数**

*   `records`:  [`RecordToInsert[]`](../interface/API%20类型定义.md) - 要插入的记录列表，每个记录包含fields属性（字段值映射）
    

根据字段类型不同，写入的字段值结构也不同，具体可以参考[《字段数据结构》](../interface/字段类型结构.md)

**返回值**

*   [`Promise<Record[]>`](../modules/Record%20模块.md) - 插入的记录对象列表
    

**示例**

```typescript
// 插入单条记录
const newRecords = await sheet.insertRecordsAsync([
  {
    fields: {
      '标题': '新客户开发计划',
      '负责人': '张三',
      '优先级': '高',
      '截止日期': '2025-12-31'
    }
  }
]);
console.log(`成功创建记录，ID: ${newRecords[0].getId()}`);

// 批量插入多条记录
const batchRecords = await sheet.insertRecordsAsync([
  {
    fields: { '客户名称': '阿里巴巴', '联系人': '马云', '状态': '已签约' }
  },
  {
    fields: { '客户名称': '腾讯', '联系人': '马化腾', '状态': '洽谈中' }
  },
  {
    fields: { '客户名称': '百度', '联系人': '李彦宏', '状态': '已联系' }
  }
]);
console.log(`成功批量创建 ${batchRecords.length} 条记录`);

```
```typescript
// 插入单条记录
const newRecords = await sheet.insertRecordsAsync([
  {
    fields: {
      '标题': '新客户开发计划',
      '负责人': '张三',
      '优先级': '高',
      '截止日期': '2025-12-31'
    }
  }
]);
Output.log(`成功创建记录，ID: ${newRecords[0].getId()}`);

// 批量插入多条记录
const batchRecords = await sheet.insertRecordsAsync([
  {
    fields: { '客户名称': '阿里巴巴', '联系人': '马云', '状态': '已签约' }
  },
  {
    fields: { '客户名称': '腾讯', '联系人': '马化腾', '状态': '洽谈中' }
  },
  {
    fields: { '客户名称': '百度', '联系人': '李彦宏', '状态': '已联系' }
  }
]);
Output.log(`成功批量创建 ${batchRecords.length} 条记录`);

```

**注意事项**

*   脚本插件/边栏插件下一次最多可以插入 **1000** 条记录（超过会报 `You may insert at most 1000 records at a time.`）
    
*   （REST OpenAPI 通道的上限是 500，不适用于插件场景）
    
*   需要有记录创建权限
    
*   字段标识符可以是字段ID或字段名称
    
*   如果记录总数超过表格限制会失败
    

### updateRecordsAsync

批量更新行记录。

```typescript
updateRecordsAsync: (records: RecordToUpdate[]) => Promise<Record[]>

```

**参数**

*   `records`: [`RecordToUpdate[]`](../interface/API%20类型定义.md) - 要更新的行记录列表，每个记录包含fields属性（字段值映射）
    

**返回值**

*   [`Promise<Record[]>`](../modules/Record%20模块.md) - 更新后的记录对象数组
    

**示例**

```typescript
// 更新单条记录
const updatedRecords = await sheet.updateRecordsAsync([
  {
    id: 'rec123456',
    fields: {
      '状态': '已完成',
      '完成时间': new Date(),
      '备注': '按时完成所有任务'
    }
  }
]);

// 批量更新多条记录状态
await sheet.updateRecordsAsync([
  {
    id: 'rec123456',
    fields: { '状态': '已完成' }
  },
  {
    id: 'rec234567',
    fields: { '状态': '处理中', '优先级': '高' }
  },
  {
    id: 'rec345678',
    fields: { '状态': '已取消', '备注': '客户需求变更' }
  }
]);

```

**注意事项**

*   脚本插件/边栏插件下一次最多可以更新 **500** 条记录（超过会报 `You may update at most 500 records at a time.`）
    
*   （REST OpenAPI 通道的上限是 100，不适用于插件场景）
    
*   需要有记录更新权限
    
*   只会更新指定的字段，未指定的字段保持不变
    
*   字段标识符可以是字段ID或字段名称
    

### deleteRecordsAsync

删除一条或多条记录。

```typescript
deleteRecordsAsync: (ids: string | string[]) => Promise<void>
```

**参数**

*   `ids`: `string | string[]` - 要删除的记录ID或ID数组
    

**返回值**

*   `Promise<void>` - 返回Promise，操作完成时解析
    

**示例**

```typescript
// 删除单条记录
await sheet.deleteRecordsAsync('rec123456');
console.log('记录已删除');

// 删除多条记录
await sheet.deleteRecordsAsync([
  'rec123456', 
  'rec234567', 
  'rec345678'
]);
console.log('多条记录已删除');

// 条件删除记录示例
// 注意：getRecordsAsync 的 filter 用的是 OpenApi.Filter 结构：
//   { combination?: 'and' | 'or', conditions: [{ field, operator, value? }] }
// operator 只能是 'equal' | 'notEqual' | 'greater' | 'greaterEqual' | 'less' |
//   'lessEqual' | 'contain' | 'notContain' | 'empty' | 'notEmpty'
// value 是数组。切勿使用 GridView 筛选的 conjunction / fieldId / 'is' 语义，两套类型不通用。
const recordsToDelete = await sheet.getRecordsAsync({
  filter: {
    combination: 'and',
    conditions: [
      {
        field: '状态',
        operator: 'equal',
        value: ['已取消']
      }
    ]
  }
});

if (recordsToDelete.records.length > 0) {
  const recordIds = recordsToDelete.records.map(record => record.getId());
  await sheet.deleteRecordsAsync(recordIds);
  console.log(`已删除 ${recordIds.length} 条已取消的记录`);
}

```
```typescript
// 删除单条记录
await sheet.deleteRecordsAsync('rec123456');
Output.log('记录已删除');

// 删除多条记录
await sheet.deleteRecordsAsync([
  'rec123456', 
  'rec234567', 
  'rec345678'
]);
Output.log('多条记录已删除');

// 条件删除记录示例
// 注意：getRecordsAsync 的 filter 用的是 OpenApi.Filter 结构：
//   { combination?: 'and' | 'or', conditions: [{ field, operator, value? }] }
// operator 只能是 'equal' | 'notEqual' | 'greater' | 'greaterEqual' | 'less' |
//   'lessEqual' | 'contain' | 'notContain' | 'empty' | 'notEmpty'
// value 是数组。切勿使用 GridView 筛选的 conjunction / fieldId / 'is' 语义，两套类型不通用。
const recordsToDelete = await sheet.getRecordsAsync({
  filter: {
    combination: 'and',
    conditions: [
      {
        field: '状态',
        operator: 'equal',
        value: ['已取消']
      }
    ]
  }
});

if (recordsToDelete.records.length > 0) {
  const recordIds = recordsToDelete.records.map(record => record.getId());
  await sheet.deleteRecordsAsync(recordIds);
  Output.log(`已删除 ${recordIds.length} 条已取消的记录`);
}

```

**注意事项**

*   脚本插件/边栏插件下一次最多可以删除 **500** 条记录（超过会报 `You may delete at most 500 records at a time.`）
    
*   （REST OpenAPI 通道的上限是 100，不适用于插件场景）
    
*   需要有记录删除权限