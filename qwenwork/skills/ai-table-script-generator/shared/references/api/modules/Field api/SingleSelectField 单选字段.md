# SingleSelectField 单选字段

SingleSelectField，继承自基础 [Field](../Field%20模块.md) 类，专门用于处理单选类型数据。用于从预设选项中选择单个值，常用于状态、类别等场景。

## 字段特有方法

### getValueAsync

获取指定记录在该单选字段中选择的选项。

```typescript
getValueAsync: (recordId: string) => Promise<SelectOption | null>

```

**参数**

*   `recordId`: `string` - 记录ID
    

**返回值**

*   [`Promise<SelectOption | null>`](../../interface/API%20类型定义.md) - 选中的选项，包含id和name属性，如果未选择则返回null
    

**示例**

```typescript
// 获取记录的选项值
const statusField = sheet.getField<SingleSelectField>('状态');
if (statusField) {
  const selectedOption = await statusField.getValueAsync('rec123456');
  if (selectedOption) {
    console.log(`选中的状态: ${selectedOption.name} (ID: ${selectedOption.id})`);
  } else {
    console.log('未选择任何状态');
  }
}

```
```typescript
// 获取记录的选项值
const statusField = sheet.getField('状态');
if (FieldBase.isFieldOfType(statusField, 'singleSelect')) {
  const selectedOption = await statusField.getValueAsync('rec123456');
  if (selectedOption) {
    Output.log(`选中的状态: ${selectedOption.name} (ID: ${selectedOption.id})`);
  } else {
    Output.log('未选择任何状态');
  }
}

```

### setValueAsync

设置指定记录在该单选字段中的选项。

```typescript
setValueAsync: (recordId: string, optionId: string) => Promise<boolean>

```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `optionId`: `string` - 选项ID
    

**返回值**

*   `Promise<boolean>`\- 操作是否成功
    

**示例**

```typescript
// 设置记录的选项值
const statusField = sheet.getField<SingleSelectField>('状态');
if (statusField) {
  // 首先获取所有选项，找到目标选项的ID
  const options = statusField.getOptions();
  const inProgressOption = options.find(opt => opt.name === '处理中');
  
  if (inProgressOption) {
    // 使用选项ID设置记录值
    const success = await statusField.setValueAsync('rec123456', inProgressOption.id);
    if (success) {
      console.log('状态已更新为处理中');
    } else {
      console.log('状态更新失败');
    }
  }
}

```
```typescript
// 设置记录的选项值
const statusField = sheet.getField('状态');
if (Base.isFieldOfType(statusField, 'singleSelect')) {
  // 首先获取所有选项，找到目标选项的ID
  const options = statusField.getOptions();
  const inProgressOption = options.find(opt => opt.name === '处理中');
  
  if (inProgressOption) {
    // 使用选项ID设置记录值
    const success = await statusField.setValueAsync('rec123456', inProgressOption.id);
    if (success) {
      Output.log('状态已更新为处理中');
    } else {
      Output.log('状态更新失败');
    }
  }
}

```

### addOption

添加一个新的选项到单选字段中。

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
const statusField = sheet.getField<SingleSelectField>('状态');
if (statusField) {
  statusField.addOption('待审核');
}

```
```typescript
// 添加一个新选项「待审核」
const statusField = sheet.getField('状态');
if (Base.isFieldOfType(statusField, 'singleSelect')) {
  statusField.addOption('待审核');
}

```

### addOptions

批量添加多个选项到单选字段中。

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
const priorityField = sheet.getField<SingleSelectField>('优先级');
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
if (statusFieldBase.isFieldOfType(priorityField, 'singleSelect')) {
  priorityField.addOptions([
    { name: '低' },
    { name: '中' },
    { name: '高' },
    { name: '紧急' }
  ]);
}

```

### getOptions

获取单选字段的所有选项。

```typescript
getOptions: () => ISelectFieldOption[]

```

**返回值**

*    [`ISelectFieldOption[]`](../../interface/API%20类型定义.md) - 选项列表，每个选项包含id、name和color属性
    

**示例**

```typescript
// 获取所有选项
const statusField = sheet.getField<SingleSelectField>('状态');
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
if (Base.isFieldOfType(statusField, 'singleSelect')) {
  const options = statusField.getOptions();
  Output.log(`共有 ${options.length} 个选项:`);
  options.forEach(option => {
    Output.log(`- ${option.name} (ID: ${option.id}, 颜色: ${option.color})`);
  });
}

```

### deleteOptionAsync

删除单选字段中的指定选项，由于删除选项会间接影响字段值，所以此方法为异步方法。

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
const statusField = sheet.getField<SingleSelectField>('状态');
if (statusField) {
  // 通过选项ID删除
  await statusField.deleteOptionAsync('opt123456');
  
  // 或通过选项名称删除
  await statusField.deleteOptionAsync('已取消');
}

```
```typescript
// 删除指定选项
const statusField = sheet.getField('状态');
if (Base.isFieldOfType(statusField, 'singleSelect')) {
  // 通过选项ID删除
  await statusField.deleteOptionAsync('opt123456');
  
  // 或通过选项名称删除
  await statusField.deleteOptionAsync('已取消');
}

```

### setOptionAsync

修改单选字段中指定选项的配置。

```typescript
setOptionAsync(nameOrId: string, config: IOptionConfig): Promise<string>

```

**参数**

*   `nameOrId`: `string` - 选项ID或选项名称
    
*   `config`: [`IOptionConfig`](../../interface/API%20类型定义.md) - 选项配置，目前支持修改name属性
    

**返回值**

*   `Promise<string>`\- 字段ID
    

**示例**

```typescript
// 修改选项名称
const statusField = sheet.getField<SingleSelectField>('状态');
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
if (Base.isFieldOfType(statusField, 'singleSelect')) {
  // 通过选项ID修改
  await statusField.setOptionAsync('opt123456', { name: '已完成' });
  
  // 或通过选项名称修改
  await statusField.setOptionAsync('进行中', { name: '处理中' });
}

```