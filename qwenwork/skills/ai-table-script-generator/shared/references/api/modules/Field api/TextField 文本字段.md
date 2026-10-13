# TextField 文本字段

`TextField`，继承自基础 [Field](../Field%20模块.md) 类，专门用于处理文本字段数据。

## 字段特有方法

### getValueAsync

获取指定记录在该文本字段的值。

```typescript
getValueAsync: (recordId: string) => Promise<string | null>
```

**参数**

*   `recordId` : `string` - 记录ID
    

**返回值**

*   `Promise<string | null>`\- 文本值，如果记录不存在或值为空则返回null
    

**示例**

```typescript
// 获取文本字段值
const textField = sheet.getField<TextField>('备注');
if (textField) {
  const text = await textField.getValueAsync('rec123456');
  console.log(`备注内容: ${text || '无'}`);
}

```
```typescript
// 获取文本字段值
const textField = sheet.getField('备注');
if (Base.isFieldOfType(textField, 'text')) {
  const text = await textField.getValueAsync('rec123456');
  Output.log(`备注内容: ${text || '无'}`);
}

```

### setValueAsync

设置指定记录在该文本字段的值。

```typescript
setValueAsync: (recordId: string, text: string): Promise<boolean>
```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `text`: `string` - 要设置的文本值
    

**返回值**

*   `Promise<boolean>`\- 设置是否成功
    

**示例**

```typescript
// 设置文本字段值
const textField = sheet.getField<TextField>('备注');
if (textField) {
  const success = await textField.setValueAsync('rec123456', '这是一条新的备注内容');
  if (success) {
    console.log('文本更新成功');
  } else {
    console.log('文本更新失败');
  }
}

```
```typescript
// 设置文本字段值
const textField = sheet.getField('备注');
if (Base.isFieldOfType(textField, 'text')) {
  const success = await textField.setValueAsync('rec123456', '这是一条新的备注内容');
  if (success) {
    Output.log('文本更新成功');
  } else {
    Output.log('文本更新失败');
  }
}

```