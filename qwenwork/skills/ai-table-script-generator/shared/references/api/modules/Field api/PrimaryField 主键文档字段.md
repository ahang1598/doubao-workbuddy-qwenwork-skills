# PrimaryField 主键文档字段

`PrimaryField`，继承自基础 [Field](../Field%20模块.md) 类，专门用于处理主键文档字段数据。

:::
PrimaryField必须是主键字段，数据表中仅主键字段可以设置为PrimaryField。
:::

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
const primayDocField = sheet.getField<PrimaryDocField>('标题');
if (primayDocField) {
  const text = await primayDocField.getValueAsync('rec123456');
}

```
```typescript
const primayDocField = sheet.getField('标题');
if (Base.isFieldOfType(primayDocField, 'primaryDoc')) {
  const text = await primayDocField.getValueAsync('rec123456');
}

```

### setValueAsync

设置指定记录在该文本字段的值。

```typescript
setValueAsync: (recordId: string, text: string) => Promise<boolean>
```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `text`: `string` - 要设置的文本值
    

**返回值**

*   `Promise<boolean>`\- 设置是否成功
    

**示例**

```typescript
const primayDocField = sheet.getField<PrimaryDocField>('标题');
if (primayDocField) {
  const success = await primayDocField.setValueAsync('rec123456', '这是一条新的内容');
  if (success) {
    console.log('更新成功');
  } else {
    console.log('更新失败');
  }
}

```
```typescript
const primayDocField = sheet.getField('标题');
if (Base.isFieldOfType(primayDocField, 'primaryDoc')) {
  const success = await primayDocField.setValueAsync('rec123456', '这是一条新的内容');
  if (success) {
    Output.log('更新成功');
  } else {
    Output.log('更新失败');
  }
}

```