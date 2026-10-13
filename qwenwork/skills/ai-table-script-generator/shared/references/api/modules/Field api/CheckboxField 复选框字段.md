# CheckboxField 复选框字段

`CheckboxField`，继承自基础 [Field](../Field%20模块.md) 类，专门用于处理开关类型的复选框字段数据。用于表示是/否、启用/禁用等二元状态。

## 字段特有方法

### getValueAsync

获取指定行记录该复选框字段的值。

```typescript
getValueAsync: (recordId: string) => Promise<boolean | null>

```

**参数**

*   `recordId` : `string` - 记录ID
    

**返回值**

*   `Promise<boolean | null>` - 复选框值(true/false)，当字段值为空时返回null
    

**示例**

```typescript
// 获取复选框字段值
const checkboxField = sheet.getField<CheckboxField>('已完成');
if (checkboxField) {
  const isChecked = await checkboxField.getValueAsync('rec123456');
  console.log(`已完成状态: ${isChecked !== null ? (isChecked ? '是' : '否') : '未设置'}`);
}

```
```typescript
// 获取复选框字段值
const checkboxField = sheet.getField('已完成');
if (Base.isFieldOfType(checkboxField, 'checkbox')) {
  const isChecked = await checkboxField.getValueAsync('rec123456');
  Output.log(`已完成状态: ${isChecked !== null ? (isChecked ? '是' : '否') : '未设置'}`);
}

```

### setValueAsync

设置指定行记录该复选框字段的值。

```typescript
setValueAsync: (recordId: string, val: boolean) => Promise<boolean>

```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `val`: `boolean` - 复选框值(true/false)
    

**返回值**

*   `Promise<boolean>` - 设置是否成功
    

**示例**

```typescript
// 设置复选框字段值
const checkboxField = sheet.getField<CheckboxField>('已完成');
if (checkboxField) {
  const success = await checkboxField.setValueAsync('rec123456', true);
  if (success) {
    console.log('复选框状态更新成功');
  } else {
    console.log('复选框状态更新失败');
  }
}

```
```typescript
// 设置复选框字段值
const checkboxField = sheet.getField('已完成');
if (Base.isFieldOfType(checkboxField, 'checkbox')) {
  const success = await checkboxField.setValueAsync('rec123456', true);
  if (success) {
    Output.log('复选框状态更新成功');
  } else {
    Output.log('复选框状态更新失败');
  }
}

```