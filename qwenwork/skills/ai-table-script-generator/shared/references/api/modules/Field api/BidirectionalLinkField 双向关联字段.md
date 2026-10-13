# BidirectionalLinkField 双向关联字段

BidirectionalLinkField 继承自基础 [Field](../Field%20模块.md)类，专门用于处理双向关联类型数据。用于在两个表之间建立双向关联关系，当在当前表中设置关联时，目标表中也会自动创建反向关联。

## 字段特有方法

### getValueAsync

获取指定记录在该双向关联字段中的关联值。

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
const linkField = sheet.getField<BidirectionalLinkField>('关联项目');
if (linkField) {
  const linkValue = await linkField.getValueAsync('rec_123');
  if (linkValue) {
    console.log(`关联的记录数量: ${linkValue.linkedRecordIds.length}`);
    
    // 打印每个关联的记录ID
    linkValue.linkedRecordIds.forEach((recordId, index) => {
      console.log(`关联记录${index + 1}: ${recordId}`);
    });
  } else {
    console.log('该记录未设置任何关联');
  }
}

```
```typescript
// 获取记录的关联值
const linkField = sheet.getField('关联项目');
if (Base.isFieldOfType(linkField, 'bidirectionalLink')) {
  const linkValue = await linkField.getValueAsync('rec_123');
  if (linkValue) {
    Output.log(`关联的记录数量: ${linkValue.linkedRecordIds.length}`);
    
    // 打印每个关联的记录ID
    linkValue.linkedRecordIds.forEach((recordId, index) => {
      Output.log(`关联记录${index + 1}: ${recordId}`);
    });
  } else {
    Output.log('该记录未设置任何关联');
  }
}

```

### setValueAsync

设置指定记录在该双向关联字段中的关联值。

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
const linkField = sheet.getField<BidirectionalLinkField>('关联项目');
if (linkField) {
  const linkValue: AssociationsValue = {
    linkedRecordIds: ['rec_project_1', 'rec_project_2']
  };
  
  const success = await linkField.setValueAsync('rec_123', linkValue);
  if (success) {
    console.log('关联设置成功');
    console.log('注意：目标表中的相关记录也会自动建立反向关联');
  } else {
    console.log('关联设置失败');
  }
}

```
```typescript
// 设置记录的关联值
const linkField = sheet.getField('关联项目');
if (Base.isFieldOfType(linkField, 'bidirectionalLink')) {
  const linkValue: AssociationsValue = {
    linkedRecordIds: ['rec_project_1', 'rec_project_2']
  };
  
  const success = await linkField.setValueAsync('rec_123', linkValue);
  if (success) {
    Output.log('关联设置成功');
    Output.log('注意：目标表中的相关记录也会自动建立反向关联');
  } else {
    Output.log('关联设置失败');
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
const linkField = sheet.getField<BidirectionalLinkField>('关联项目');
if (linkField) {
  const fieldId = linkField.setLinkedSheetId('abcdefg');
  console.log(`成功设置关联目标表，字段ID: ${fieldId}`);
}

```
```typescript
// 设置关联的目标表
const linkField = sheet.getField('关联项目');
if (Base.isFieldOfType(linkField, 'bidirectionalLink')) {
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
const linkField = sheet.getField<BidirectionalLinkField>('关联项目');
if (linkField) {
  const linkedSheetId = linkField.getLinkedSheetId();
  console.log(`关联的目标表ID: ${linkedSheetId}`);
}

```
```typescript
// 获取关联的目标表ID
const linkField = sheet.getField('关联项目');
if (Base.isFieldOfType(linkField, 'bidirectionalLink')) {
  const linkedSheetId = linkField.getLinkedSheetId();
  Output.log(`关联的目标表ID: ${linkedSheetId}`);
}

```

### setMultiple

设置是否允许关联多条记录。

```typescript
setMultiple: (multiple: boolean) => string

```

**参数**

*   `multiple`: `boolean` - 是否允许多选，true表示可以关联多条记录，false表示只能关联一条记录
    

**返回值**

*   `string` - 字段ID
    

**示例**

```typescript
// 设置允许关联多条记录
const linkField = sheet.getField<BidirectionalLinkField>('关联任务');
if (linkField) {
  const fieldId = linkField.setMultiple(true);  // 允许关联多个任务
  console.log(`已设置为允许多选，字段ID: ${fieldId}`);
}

// 设置只允许关联一条记录
const ownerField = sheet.getField<BidirectionalLinkField>('负责人');
if (ownerField) {
  const fieldId = ownerField.setMultiple(false);  // 只能关联一个负责人
  console.log(`已设置为单选模式，字段ID: ${fieldId}`);
}

```
```typescript
// 设置允许关联多条记录
const linkField = sheet.getField<BidirectionalLinkField>('关联任务');
if (Base.isFieldOfType(linkField, 'bidirectionalLink')) {
  const fieldId = linkField.setMultiple(true);  // 允许关联多个任务
  Output.log(`已设置为允许多选，字段ID: ${fieldId}`);
}

// 设置只允许关联一条记录
const ownerField = sheet.getField<BidirectionalLinkField>('负责人');
if (Base.isFieldOfType(ownerField, 'bidirectionalLink')) {
  const fieldId = ownerField.setMultiple(false);  // 只能关联一个负责人
  Output.log(`已设置为单选模式，字段ID: ${fieldId}`);
}

```

### getMultiple

获取当前是否允许关联多条记录的设置。

```typescript
getMultiple: () => boolean

```

**返回值**

*   `boolean` - true表示允许多选，false表示只能单选
    

**示例**

```typescript
// 检查多选设置
const linkField = sheet.getField<BidirectionalLinkField>('关联项目');
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
const linkField = sheet.getField('关联项目');
if (Base.isFieldOfType(linkField, 'bidirectionalLink')) {
  const isMultiple = linkField.getMultiple();
  if (isMultiple) {
    Output.log('当前允许关联多条记录');
  } else {
    Output.log('当前只允许关联一条记录');
  }
}

```