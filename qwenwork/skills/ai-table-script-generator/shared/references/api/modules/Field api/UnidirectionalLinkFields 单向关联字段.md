# UnidirectionalLinkFields 单向关联字段

UnidirectionalLinkField 继承自基础 [Field](../Field%20模块.md)类，专门用于处理单向关联类型数据。用于从当前表向目标表建立关联关系，只在当前表中记录关联信息，不会在目标表中创建反向关联。

## 字段特有方法

### getValueAsync

获取指定记录在该单向关联字段中的关联值。

```typescript
getValueAsync: (recordId: string) => Promise<AssociationsValue | null>

```

**参数**

*   `recordId`: `string` - 记录ID
    

**返回值**

*   [`Promise<AssociationsValue | null>`](../../interface/API%20类型定义.md) - 关联值对象，如果未设置关联则返回null
    

**示例**

```typescript
// 获取记录的关联值
const linkField = sheet.getField<UnidirectionalLinkField>('参考方案');
if (linkField) {
  const linkValue = await linkField.getValueAsync('rec_project_123');
  if (linkValue) {
    console.log(`关联的记录数量: ${linkValue.linkedRecordIds.length}`);
    
    // 打印每个关联的记录ID
    linkValue.linkedRecordIds.forEach((recordId, index) => {
      console.log(`参考方案${index + 1}: ${recordId}`);
    });
  } else {
    console.log('该项目未设置参考方案');
  }
}

```
```typescript
// 获取记录的关联值
const linkField = sheet.getField('参考方案');
if (Base.isFieldOfType(linkField, 'unidirectionalLink')) {
  const linkValue = await linkField.getValueAsync('rec_project_123');
  if (linkValue) {
    Output.log(`关联的记录数量: ${linkValue.linkedRecordIds.length}`);
    
    // 打印每个关联的记录ID
    linkValue.linkedRecordIds.forEach((recordId, index) => {
      Output.log(`参考方案${index + 1}: ${recordId}`);
    });
  } else {
    Output.log('该项目未设置参考方案');
  }
}

```

### setValueAsync

设置指定记录在该单向关联字段中的关联值。

```typescript
setValueAsync: (recordId: string, value: AssociationsValue) => Promise<boolean>

```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `value`: [`AssociationsValue`](../../interface/API%20类型定义.md) - 关联值对象
    

**返回值**

*   `Promise<boolean>` - 操作是否成功
    

**示例**

```typescript
// 设置记录的关联值
const linkField = sheet.getField<UnidirectionalLinkField>('技术栈');
if (linkField) {
  const linkValue: AssociationsValue = {
    linkedRecordIds: ['rec_1', 'rec_2'],
  };
  
  const success = await linkField.setValueAsync('rec_123', linkValue);
  if (success) {
    console.log('技术栈关联设置成功');
    console.log('注意：这是单向关联，目标表中不会创建反向关联');
  } else {
    console.log('技术栈关联设置失败');
  }
}

```
```typescript
// 设置记录的关联值
const linkField = sheet.getField('技术栈');
if (Base.isFieldOfType(linkField, 'unidirectionalLink')) {
  const linkValue: AssociationsValue = {
    linkedRecordIds: ['rec_1', 'rec_2'],
  };
  
  const success = await linkField.setValueAsync('rec_123', linkValue);
  if (success) {
    Output.log('技术栈关联设置成功');
    Output.log('注意：这是单向关联，目标表中不会创建反向关联');
  } else {
    Output.log('技术栈关联设置失败');
  }
}

```

### setLinkedSheetId

设置关联的目标数据表ID。

```typescript
setLinkedSheetId: (linkedSheetId: string) => string

```

**参数**

*   `linkedSheetId`: `string` - 目标数据表ID
    

**返回值**

*   `string` - 字段ID
    

**示例**

```typescript
// 设置关联的目标表
const linkField = sheet.getField<UnidirectionalLinkField>('参考资料');
if (linkField) {
  const fieldId = linkField.setLinkedSheetId('abcdefg');
  console.log(`成功设置关联目标表，字段ID: ${fieldId}`);
}

```
```typescript
// 设置关联的目标表
const linkField = sheet.getField('参考资料');
if (Base.isFieldOfType(linkField, 'unidirectionalLink')) {
  const fieldId = linkField.setLinkedSheetId('abcdefg');
  Output.log(`成功设置关联目标表，字段ID: ${fieldId}`);
}

```

### getLinkedSheetId

获取当前关联的目标数据表ID。

```typescript
getLinkedSheetId: () => string

```

**返回值**

*   `string` - 目标数据表ID
    

**示例**

```typescript
// 获取关联的目标表ID
const linkField = sheet.getField<UnidirectionalLinkField>('参考资料');
if (linkField) {
  const linkedSheetId = linkField.getLinkedSheetId();
  console.log(`关联的目标表ID: ${linkedSheetId}`);
}

```
```typescript
// 获取关联的目标表ID
const linkField = sheet.getField('参考资料');
if (Base.isFieldOfType(linkField, 'unidirectionalLink')) {
  const linkedSheetId = linkField.getLinkedSheetId();
  Output.log(`关联的目标表ID: ${linkedSheetId}`);
}

```

### setMultiple

设置是否允许关联多条记录。

```typescript
setMultiple(multiple: boolean): string

```

**参数**

*   `multiple`: `boolean` - 是否允许多选，true表示可以关联多条记录，false表示只能关联一条记录
    

**返回值**

*   `string` - 字段ID
    

**示例**

```typescript
// 设置允许关联多条记录
const linkField = sheet.getField<UnidirectionalLinkField>('相关文档');
if (linkField) {
  const fieldId = linkField.setMultiple(true);  // 允许关联多个文档
  console.log(`已设置为允许多选，字段ID: ${fieldId}`);
}

// 设置只允许关联一条记录
const templateField = sheet.getField<UnidirectionalLinkField>('使用模板');
if (templateField) {
  const fieldId = templateField.setMultiple(false);  // 只能选择一个模板
  console.log(`已设置为单选模式，字段ID: ${fieldId}`);
}

```
```typescript
// 设置允许关联多条记录
const linkField = sheet.getField('相关文档');
if (Base.isFieldOfType(linkField, 'unidirectionalLink')) {
  const fieldId = linkField.setMultiple(true);  // 允许关联多个文档
  Output.log(`已设置为允许多选，字段ID: ${fieldId}`);
}

// 设置只允许关联一条记录
const templateField = sheet.getField('使用模板');
if (Base.isFieldOfType(templateField, 'unidirectionalLink')) {
  const fieldId = templateField.setMultiple(false);  // 只能选择一个模板
  Output.log(`已设置为单选模式，字段ID: ${fieldId}`);
}

```

### getMultiple

获取当前是否允许关联多条记录的设置。

```typescript
getMultiple(): boolean

```

**返回值**

*   `boolean` - true表示允许多选，false表示只能单选
    

**示例**

```typescript
// 检查多选设置
const linkField = sheet.getField<UnidirectionalLinkField>('参考案例');
if (linkField) {
  const isMultiple = linkField.getMultiple();
  if (isMultiple) {
    console.log('当前允许关联多条记录');
  } else {
    console.log('当前只允许关联一条记录');
  }
}

```
```typescript
// 检查多选设置
const linkField = sheet.getField('参考案例');
if (Base.isFieldOfType(templateField, 'unidirectionalLink')) {
  const isMultiple = linkField.getMultiple();
  if (isMultiple) {
    Output.log('当前允许关联多条记录');
  } else {
    Output.log('当前只允许关联一条记录');
  }
}

```