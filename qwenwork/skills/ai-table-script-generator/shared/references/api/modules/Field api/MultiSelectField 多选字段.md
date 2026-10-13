# MultiSelectField 多选字段

MultiSelectField 继承自基础 [`Field`](../Field%20模块.md)类，专门用于处理多选字段类型数据，用于从预设选项中选择多个值。

## 字段特有方法

### getValueAsync

获取指定记录在该多选字段中选择的选项。

```typescript
getValueAsync: (recordId: string) => Promise<SelectOption[] | null>

```

**参数**

*   `recordId`: `string` - 记录ID
    

**返回值**

*   [`Promise<SelectOption[] | null>`](../../interface/API%20类型定义.md) - 选中的选项数组，包含id和name属性，如果未选择则返回null
    

**示例**

```typescript
// 获取记录的多选选项值
const tagsField = sheet.getField<MultipleSelectField>('标签');
if (tagsField) {
  const selectedTags = await tagsField.getValueAsync('rec123456');
  if (selectedTags.length > 0) {
    console.log(`选中的标签: ${selectedTags.map(tag => tag.name).join(', ')}`);
  } else {
    console.log('未选择任何标签');
  }
}
```
```typescript
// 获取记录的多选选项值
const tagsField = sheet.getField('标签');
if (Base.isFieldOfType(tagsField, 'multipleSelect')) {
  const selectedTags = await tagsField.getValueAsync('rec123456');
  if (selectedTags.length > 0) {
    Output.log(`选中的标签: ${selectedTags.map(tag => tag.name).join(', ')}`);
  } else {
    Output.log('未选择任何标签');
  }
}
```

### setValueAsync

设置指定记录在该多选字段中的选项。

```typescript
setValueAsync: (recordId: string, optionId: string | string[]) => Promise<boolean>

```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `optionId`: `string | string[]` - 选项ID 数组
    

**返回值**

*   `Promise<boolean>`\- 操作是否成功
    

**示例**

```typescript
// 设置记录的多选选项值
const tagsField = sheet.getField<MultipleSelectField>('标签');
if (tagsField) {
  // 获取所有选项
  const options = tagsField.getOptions();
  
  // 找到需要的选项ID
  const urgentTag = options.find(opt => opt.name === '紧急');
  const importantTag = options.find(opt => opt.name === '重要');
  
  if (urgentTag && importantTag) {
    // 设置多个标签
    const success = await tagsField.setValueAsync('rec123456', [urgentTag.id, importantTag.id]);
    if (success) {
      console.log('已将记录标记为"紧急"和"重要"');
    }
  }
  
  // 也可以设置单个标签
  const followupTag = options.find(opt => opt.name === '需跟进');
  if (followupTag) {
    await tagsField.setValueAsync('rec234567', followupTag.id);
    console.log('已将记录标记为"需跟进"');
  }
}
```
```typescript
// 设置记录的多选选项值
const tagsField = sheet.getField<MultipleSelectField>('标签');
if (Base.isFieldOfType(tagsField, 'multipleSelect')) {
  // 获取所有选项
  const options = tagsField.getOptions();
  
  // 找到需要的选项ID
  const urgentTag = options.find(opt => opt.name === '紧急');
  const importantTag = options.find(opt => opt.name === '重要');
  
  if (urgentTag && importantTag) {
    // 设置多个标签
    const success = await tagsField.setValueAsync('rec123456', [urgentTag.id, importantTag.id]);
    if (success) {
      Output.log('已将记录标记为"紧急"和"重要"');
    }
  }
  
  // 也可以设置单个标签
  const followupTag = options.find(opt => opt.name === '需跟进');
  if (followupTag) {
    await tagsField.setValueAsync('rec234567', followupTag.id);
    Output.log('已将记录标记为"需跟进"');
  }
}
```

### addOption

添加一个新的选项到多选字段中。

```typescript
addOption: (name: string) => string

```

**参数**

*   `name`: `string` - 选项名称
    

**返回值**

*   `string` - 字段ID
    

**示例**

```typescript
// 添加一个新选项「待审核」
const statusField = sheet.getField<MultiSelectField>('状态');
if (statusField) {
  statusField.addOption('待审核');
}

```
```typescript
// 添加一个新选项「待审核」
const statusField = sheet.getField('状态');
if (Base.isFieldOfType(statusField, 'multipleSelect')) {
  statusField.addOption('待审核');
}

```

### addOptions

批量添加多个选项到多选字段中。

```typescript
addOptions: (optionList: { name: string }[]) => string
```

**参数**

*   `optionList`: `{ name: string }[]` - 选项列表，每个选项包含名称
    

**返回值**

*   `string` - 字段ID
    

**示例**

```typescript
// 批量添加多个选项
const priorityField = sheet.getField<MultiSelectField>('优先级');
if (priorityField) {
  priorityField.addOptions([
    { name: '低' },
    { name: '中' },
    { name: '高' },
    { name: '紧急' }
  ]);
}

```
```typescript
// 批量添加多个选项
const priorityField = sheet.getField('优先级');
if (Base.isFieldOfType(priorityField, 'multipleSelect')) {
  priorityField.addOptions([
    { name: '低' },
    { name: '中' },
    { name: '高' },
    { name: '紧急' }
  ]);
}

```

### getOptions

获取多选字段的所有选项。

```typescript
getOptions: () => ISelectFieldOption[]

```

**返回值**

*   [`ISelectFieldOption[]`](../../interface/API%20类型定义.md) - 选项列表，每个选项包含id、name和color属性
    

**示例**

```typescript
// 获取所有选项
const statusField = sheet.getField<MultiSelectField>('状态');
if (statusField) {
  const options = statusField.getOptions();
  console.log(`共有 ${options.length} 个选项:`);
  options.forEach(option => {
    console.log(`- ${option.name} (ID: ${option.id}, 颜色: ${option.color})`);
  });
}

```
```typescript
// 获取所有选项
const statusField = sheet.getField('状态');
if (Base.isFieldOfType(statusField, 'multipleSelect')) {
  const options = statusField.getOptions();
  Output.log(`共有 ${options.length} 个选项:`);
  options.forEach(option => {
    Output.log(`- ${option.name} (ID: ${option.id}, 颜色: ${option.color})`);
  });
}

```

### deleteOptionAsync

删除多选字段中的指定选项，由于删除选项会间接影响字段值，所以此方法为异步方法。

```typescript
deleteOptionAsync: (idOrName: string) => Promise<string>
```

**参数**

*   `idOrName`: `string` - 选项ID或选项名称
    

**返回值**

*   `Promise<string>`\- 字段ID
    

**示例**

```typescript
// 删除指定选项
const statusField = sheet.getField<MultiSelectField>('状态');
if (statusField) {
  // 通过选项ID删除
  await statusField.deleteOptionAsync('opt123456');
  
  // 或通过选项名称删除
  await statusField.deleteOptionAsync('已取消');
}

```
```typescript
// 删除指定选项
const statusField = sheet.getField<MultiSelectField>('状态');
if (Base.isFieldOfType(statusField, 'multipleSelect')) {
  // 通过选项ID删除
  await statusField.deleteOptionAsync('opt123456');
  
  // 或通过选项名称删除
  await statusField.deleteOptionAsync('已取消');
}
Base.isFieldOfType(statusField, 'multipleSelect')

```

### setOptionAsync

修改多选字段中指定选项的配置。

```typescript
setOptionAsync: (nameOrId: string, config: IOptionConfig) => Promise<string>

```

**参数**

*   `nameOrId`: `string` - 选项ID或选项名称
    
*   `config`: [`IOptionConfig`](../../interface/API%20类型定义.md) - 选项配置，目前支持修改name属性
    

**返回值**

*   `Promise<string>`\- 字段ID
    

**示例**

```typescript
// 修改选项名称
const statusField = sheet.getField<MultiSelectField>('状态');
if (statusField) {
  // 通过选项ID修改
  await statusField.setOptionAsync('opt123456', { name: '已完成' });
  
  // 或通过选项名称修改
  await statusField.setOptionAsync('进行中', { name: '处理中' });
}

```
```typescript
// 修改选项名称
const statusField = sheet.getField('状态');
if (Base.isFieldOfType(statusField, 'multipleSelect')) {
  // 通过选项ID修改
  await statusField.setOptionAsync('opt123456', { name: '已完成' });
  
  // 或通过选项名称修改
  await statusField.setOptionAsync('进行中', { name: '处理中' });
}

```