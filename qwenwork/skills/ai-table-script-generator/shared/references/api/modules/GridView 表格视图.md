# GridView 表格视图

数据表中的表格视图，提供了访问和操作视图配置的方法，包括字段显示、筛选条件、排序等功能。

## 基本信息方法

### sheetId

获取当前视图所属的数据表ID。

```typescript
sheetId: string

```

**返回值**

*   `string` - 数据表ID
    

**示例**

```typescript
const view = sheet.getView('view123');
const gridView = view.asGridView();
console.log(`视图所属数据表ID: ${gridView.sheetId}`);

```
```typescript
const view = sheet.getView('view123');
const gridView = view.asGridView();
Output.log(`视图所属数据表ID: ${gridView.sheetId}`);

```

### getName

获取视图名称。

```typescript
getName: () => string

```

**返回值**

*   `string` - 视图名称
    

**示例**

```typescript
const viewName = gridView.getName();
console.log(`视图名称: ${viewName}`);

```
```typescript
const viewName = gridView.getName();
Output.log(`视图名称: ${viewName}`);

```

### getType

获取视图类型。

```typescript
getType: () => 'Grid'

```

**返回值**

*   `'Grid'` - 视图类型，总是返回 'Grid'
    

**示例**

```typescript
const viewType = gridView.getType();
console.log(`视图类型: ${viewType}`); // 输出: 视图类型: Grid

```
```typescript
const viewType = gridView.getType();
Output.log(`视图类型: ${viewType}`); // 输出: 视图类型: Grid

```

### getMeta

获取表格视图元信息。

```typescript
getMeta: () => IGridViewMeta

```

**返回值**

*   [`IGridViewMeta`](../interface/API%20类型定义.md) - 包含视图ID、名称、类型和属性的元信息对象
    

**示例**

```typescript
const meta = gridView.getMeta();
console.log('视图元信息:');
console.log(`- ID: ${meta.id}`);
console.log(`- 名称: ${meta.name}`);
console.log(`- 类型: ${meta.type}`);
if (meta.property.hierarchyConfig.fieldId) {
  console.log(`- 层级字段: ${meta.property.hierarchyConfig.fieldId}`);
}
if (meta.property.filterInfo) {
  console.log(`- 筛选条件数量: ${meta.property.filterInfo.conditions.length}`);
}

```
```typescript
const meta = gridView.getMeta();
Output.log('视图元信息:');
Output.log(`- ID: ${meta.id}`);
Output.log(`- 名称: ${meta.name}`);
Output.log(`- 类型: ${meta.type}`);
if (meta.property.hierarchyConfig.fieldId) {
  Output.log(`- 层级字段: ${meta.property.hierarchyConfig.fieldId}`);
}
if (meta.property.filterInfo) {
  Output.log(`- 筛选条件数量: ${meta.property.filterInfo.conditions.length}`);
}

```

## 字段管理方法

### getVisibleFieldIdList

获取可见字段的ID列表。

```typescript
getVisibleFieldIdList: () => string[]
```

**返回值**

*   `string[]` - 可见字段ID数组
    

**示例**

```typescript
const view = sheet.getView('view123');
const gridView = view.asGridView();
const visibleFields = gridView.getVisibleFieldIdList();
console.log('可见字段列表:');
visibleFields.forEach(fieldId => {
  console.log(`- ${fieldId}`);
});

```
```typescript
const view = sheet.getView('view123');
const gridView = view.asGridView();
const visibleFields = gridView.getVisibleFieldIdList();
Output.log('可见字段列表:');
visibleFields.forEach(fieldId => {
  Output.log(`- ${fieldId}`);
});

```

### showField

显示字段。

```typescript
showField: (fieldId: string | string[]) => boolean

```

**参数**

*   `fieldId` - 要显示的字段ID，可以是单个字段ID或字段ID数组
    

**返回值**

*   `boolean` - 是否操作成功
    

**示例**

```typescript
// 显示单个字段
gridView.showField('field123');

// 显示多个字段
gridView.showField(['field123', 'field456', 'field789']);

```

### hideField

隐藏字段。

```typescript
hideField: (fieldId: string | string[]) => boolean

```

**参数**

*   `fieldId` - 要隐藏的字段ID，可以是单个字段ID或字段ID数组。
    

**返回值**

*   `boolean` - 是否操作成功
    

**重要提示**

主键字段禁止隐藏。

**示例**

```typescript
// 隐藏单个字段
gridView.hideField('field123');

// 隐藏多个字段
gridView.hideField(['field123', 'field456']);

```

### getFieldWidth

获取字段宽度。

```typescript
getFieldWidth: (fieldId: string) => number

```

**参数**

*   `fieldId` - 字段ID
    

**返回值**

*   `number` - 字段宽度（像素）
    

**示例**

```typescript
const width = gridView.getFieldWidth('field123');
console.log(`字段宽度: ${width}px`);

```
```typescript
const width = gridView.getFieldWidth('field123');
Output.log(`字段宽度: ${width}px`);

```

### getFieldWidths

获取所有字段的宽度映射。

```typescript
getFieldWidths: () => FieldWidths

```

**返回值**

*   [`FieldWidths`](../interface/API%20类型定义.md) - 字段名到宽度的映射对象
    

**示例**

```typescript
const widths = gridView.getFieldWidths();
for (const key in widths) {
  console.log(`字段${key}的宽度为${widths[key]}px。`);
}

```
```typescript
const widths = gridView.getFieldWidths();
for (const key in widths) {
  console.log(`字段${key}的宽度为${widths[key]}px。`);
}

```

### setFieldWidth

设置字段宽度。

```typescript
setFieldWidth: (fieldId: string, width: number) => boolean

```

**参数**

*   `fieldId` - 字段ID
    
*   `width` - 字段宽度（像素），必须在最小宽度和最大宽度之间
    

**返回值**

*   `boolean` - 是否设置成功
    

**示例**

```typescript
// 设置字段宽度为200像素
const success = gridView.setFieldWidth('field123', 200);

```

### setFieldWidths

设置字段宽度。

```typescript
setFieldWidths: (fieldWidths: FieldWidths) => GridView

```

**参数**

*   `fieldWidths` - [`FieldWidths`](../interface/API%20类型定义.md) 字段名到宽度的映射对象
    

**返回值**

*   `GridView` - 自身视图对象
    

**示例**

```typescript
gridView.setFieldWidths({
  'field123': 200,
  'field456': 100,
});

```

## 记录管理方法

### getVisibleRecordIdListAsync

获取可见记录的ID列表。

```typescript
getVisibleRecordIdListAsync: () => Promise<string[]>


```

**返回值**

*   `Promise<string[]>` - 可见记录 ID 数组
    

**示例**

```typescript
const visibleRecordIds = await gridView.getVisibleRecordIdListAsync();
console.log('可见记录列表:', visibleRecordIds);

```
```typescript
const visibleRecordIds = await gridView.getVisibleRecordIdListAsync();
Output.log('可见记录列表:', visibleRecordIds);

```

## 填色方法

### getFillColorInfo

获取当前的填色规则信息。

```typescript
getFillColorInfo: () => IFillColorInfo | null;

```

**返回值**

*   [`IFillColorInfo | null`](../interface/API%20类型定义.md) - 筛选信息对象，如果没有筛选条件则返回null
    

**示例**

```typescript
const fillColorInfo = gridView.getFillColorInfo();

```

### addFillColorRuleAsync

新增填色规则。

```typescript
addFillColorRuleAsync: (params: IAddFillColorRuleParams) => Promise<boolean>;

```

**参数**

*   `params` - [`IAddFillColorRuleParams`](../interface/API%20类型定义.md) - 填色规则参数
    

**返回值**

*   `Promise<boolean>` - 是否操作成功
    

**重要提示**

调用该API时，并不会保存修改的设置，如果需要保存则需要额外调用 `view.applySetting()`

**示例**

```typescript
// 添加一个填色规则
const success = await gridView.addFillColorRuleAsync({
  type: FillColorType.Column,
  fieldId: 'fieldId123',
  format: {
    color: '1',
  }
});

// 保存设置
gridView.applySetting();

```

### updateFillColorRuleAsync

更新填色规则。

```typescript
updateFillColorRuleAsync: (params: IUpdateFillColorRuleParams) => Promise<boolean>;

```

**参数**

*   `params` - [`IUpdateFillColorRuleParams`](../interface/API%20类型定义.md) - 填色规则参数
    

**返回值**

*   `Promise<boolean>` - 是否操作成功
    

**重要提示**

调用该API时，并不会保存修改的设置，如果需要保存则需要额外调用 `view.applySetting()`

**示例**

```typescript
// 添加一个填色规则
const success = await gridView.updateFillColorRuleAsync({
  ruleId: 'ruleId123'
  type: FillColorType.Column,
  fieldId: 'fieldId123',
  format: {
    color: '1',
  }
});

// 保存设置
gridView.applySetting();

```

### deleteFillColorRuleAsync

删除填色规则。

```typescript
deleteFillColorRuleAsync: (ruleId: string) => Promise<boolean>;

```

**参数**

*   `ruleId` - `string` - 填色规则参数
    

**返回值**

*   `Promise<boolean>` - 是否操作成功
    

**重要提示**

调用该API时，并不会保存修改的设置，如果需要保存则需要额外调用 `view.applySetting()`

**示例**

```typescript
// 删除一个填色规则
const success = await gridView.deleteFillColorRuleAsync(ruleId: 'ruleId123');

// 保存设置
gridView.applySetting();

```

## 筛选条件管理方法

### getFilterInfo

获取当前的筛选信息。

```typescript
getFilterInfo: () => IFilterInfo;

```

**返回值**

*   [`IFilterInfo | null`](../interface/API%20类型定义.md) - 筛选信息对象，如果没有筛选条件则返回null
    

**示例**

```typescript
const filterInfo = gridView.getFilterInfo();
if (filterInfo) {
  console.log(`筛选条件连接方式: ${filterInfo.conjunction}`);
  console.log('筛选条件列表:');
  filterInfo.conditions.forEach((condition, index) => {
    console.log(`- 条件${index + 1}: ${condition.fieldId} ${condition.operator} ${condition.value}`);
  });
} else {
  console.log('没有设置筛选条件');
}

```
```typescript
const filterInfo = gridView.getFilterInfo();
if (filterInfo) {
  console.log(`筛选条件连接方式: ${filterInfo.conjunction}`);
  console.log('筛选条件列表:');
  filterInfo.conditions.forEach((condition, index) => {
    console.log(`- 条件${index + 1}: ${condition.fieldId} ${condition.operator} ${condition.value}`);
  });
} else {
  console.log('没有设置筛选条件');
}

```

### addFilterConditionAsync

新增筛选条件。

```typescript
addFilterConditionAsync: (param: IAddFilterConditionParams) => Promise<boolean>

```

**参数**

*   `param` - [`IAddFilterConditionParams`](../interface/API%20类型定义.md) 筛选条件参数，可以是单个条件或条件数组
    

**返回值**

*   `Promise<boolean>` - 是否新增成功
    

**重要提示**

调用该API时，并不会保存修改的设置，如果需要保存则需要额外调用 `view.applySetting()`

**示例**

```typescript
// 添加单个筛选条件
await gridView.addFilterConditionAsync({
  fieldId: 'field123',
  operator: FilterOperator.Contains,
  value: '重要'
});

// 添加多个筛选条件
await gridView.addFilterConditionAsync([
  {
    fieldId: 'field123',
    operator: FilterOperator.Contains,
    value: '重要'
  },
  {
    fieldId: 'field456',
    operator: FilterOperator.IsNotEmpty
  }
]);

// 保存设置
gridView.applySetting();

```

### deleteFilterConditionAsync

删除筛选条件。

```typescript
deleteFilterConditionAsync: (conditionId: string) => Promise<boolean>

```

**参数**

*   `conditionId` - 要删除的筛选条件ID（格式：fieldId\_index）
    

**返回值**

*   `Promise<Boolean>` - 是否删除成功
    

**重要提示**

调用该API时，并不会保存修改的设置，如果需要保存则需要额外调用 `view.applySetting()`

**示例**

```typescript
// 删除指定的筛选条件
await gridView.deleteFilterConditionAsync('field123_0');

// 保存设置
gridView.applySetting();

```

### updateFilterConditionAsync

更新筛选条件。

```typescript
updateFilterConditionAsync: (param: IUpdateFilterConditionParams) => Promise<boolean>

```

**参数**

*   `param` - [`IUpdateFilterConditionParams`](../interface/API%20类型定义.md) 更新参数，可以是单个条件或条件数组，需要包含conditionId来标识要更新的条件
    

**返回值**

*   `Promise<boolean>` - 是否更新成功
    

**重要提示**

调用该API时，并不会保存修改的设置，如果需要保存则需要额外调用 `view.applySetting()`

**示例**

```typescript
// 更新单个筛选条件
await gridView.updateFilterConditionAsync({
  conditionId: 'field123_0',
  fieldId: 'field123',
  operator: FilterOperator.IsNot,
  value: '已完成'
});

// 更新多个筛选条件
await gridView.updateFilterConditionAsync([
  {
    conditionId: 'field123_0',
    fieldId: 'field123',
    operator: FilterOperator.Contains,
    value: '进行中'
  },
  {
    conditionId: 'field456_1',
    fieldId: 'field456',
    operator: FilterOperator.IsGreater,
    value: 100
  }
]);

// 保存设置
gridView.applySetting();

```

### setFilterConjunction

设置筛选条件之间的关系。

```typescript
setFilterConjunction: (conjunction: FilterConjunction) => boolean

```

**参数**

*   `conjunction` - [`FilterConjunction`](../interface/API%20类型定义.md) 筛选条件连接方式，'and' 表示满足所有条件，'or' 表示满足任一条件
    

**返回值**

*   `boolean` - 是否设置成功
    

**重要提示**

调用该API时，并不会保存修改的设置，如果需要保存则需要额外调用 `view.applySetting()`

**示例**

```typescript
// 设置为"且"关系（满足所有条件）
gridView.setFilterConjunction(FilterConjunction.And);

// 设置为"或"关系（满足任一条件）
gridView.setFilterConjunction(FilterConjunction.Or);

// 保存设置
gridView.applySetting();

```

## 设置管理方法

### applySetting

将设置的分组/筛选/排序等视图配置提交，同步给其他用户。

```typescript
applySetting: () => void

```

**返回值**

*   `void` - 无返回值
    

**示例**

```typescript
// 批量修改视图设置
await gridView.addFilterConditionAsync({
  fieldId: 'status',
  operator: FilterOperator.Is,
  value: '进行中'
});

gridView.hideField(['field1', 'field2']);
gridView.setFieldWidth('field3', 200);

// 最后统一保存所有设置
gridView.applySetting();

```

## 使用示例

### 完整的视图管理流程

```typescript
// 获取全部视图
const views = sheet.getViews();

// 获取类型为Grid的视图
const view = views.find((view) => view.getType() === 'Grid');

// 转为表格视图
const gridView = view.asGridView();

// 检查视图基本信息
const meta = gridView.getMeta();
console.log(`正在操作视图: ${meta.name} (${meta.type})`);

// 管理字段显示
const visibleFields = gridView.getVisibleFieldIdList();
console.log(`当前可见字段: ${visibleFields.length} 个`);

// 隐藏不需要的字段
gridView.hideField(['field1', 'field2']);

// 调整字段宽度
gridView.setFieldWidth('titleField', 300);
gridView.setFieldWidth('statusField', 120);

// 设置筛选条件
await gridView.addFilterConditionAsync([
  {
    fieldId: 'statusField',
    operator: FilterOperator.IsNot,
    value: '已完成'
  },
  {
    fieldId: 'priorityField',
    operator: FilterOperator.IsGreater,
    value: 3
  }
]);

// 设置筛选条件为"且"关系
gridView.setFilterConjunction(FilterConjunction.And);

// 保存所有设置
gridView.applySetting();

// 验证设置结果
const updatedFilter = gridView.getFilterInfo();
console.log(`设置完成，当前有 ${updatedFilter?.conditions.length || 0} 个筛选条件`);

```