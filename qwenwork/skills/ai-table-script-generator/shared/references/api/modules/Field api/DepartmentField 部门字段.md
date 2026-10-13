# DepartmentField 部门字段

`DepartmentField` 继承自基础 [`Field`](../Field%20模块.md)类，专门用于处理部门类型数据。

在读写群组字段前，请先了解钉钉部门deptId概念：

:::
**deptId**

deptId用于唯一识别组织部门。

[https://open.dingtalk.com/document/development/operations-related-to-address-book-departments: https://open.dingtalk.com/document/development/operations-related-to-address-book-departments](https://open.dingtalk.com/document/development/operations-related-to-address-book-departments)
:::

## 字段特有方法

### getValueAsync

获取指定记录在该部门字段中选择的部门。

```typescript
getValueAsync: (recordId: string) => Promise<DepartmentCellValue[] | null>

```

**参数**

*   `recordId`: `string` - 记录ID
    

**返回值**

*   [`Promise<DepartmentCellValue[] | null>`](../../interface/API%20类型定义.md)\- 选中的部门，返回部门名称和部门ID
    

**示例**

```typescript
// 获取记录的部门值
const departmentField = sheet.getField<DepartmentField>('部门');
if (departmentField) {
  const departments = await departmentField.getValueAsync('rec123456');
  console.log('查询到企业部门：', departments.map((dept) => (`部门名称：${dept.name}|部门ID: ${dept.openConversationId}`)).join('\n'));
}
```
```typescript
// 获取记录的部门值
const departmentField = sheet.getField('部门');
if (Base.isFieldOfType(departmentField, 'department')) {
  const users = await departmentField.getValueAsync('rec123456');
  Output.log('查询到企业部门：', departments.map((dept) => (`部门名称：${dept.name}|部门ID: ${dept.openConversationId}`)).join('\n'));
}
```

### setValueAsync

设置指定记录在该部门字段中的部门值。

```typescript
setValueAsync: (recordId: string, value: DepartmentCellValue[]) => Promise<boolean>

```

**参数**

*   `recordId`: `string` - 记录ID
    
*   `value`: [`DepartmentCellValue[]`](../../interface/API%20类型定义.md) - 部门值，支持传入deptId
    

**返回值**

*   `Promise<boolean>`\- 操作是否成功
    

**示例**

```typescript
// 设置记录的部门值
const departmentField = sheet.getField<DeparmentField>('部门');
if (departmentField) {
  const success = await departmentField.setValueAsync('rec123456', [{
    deptId: '1234',
  }, {
    deptId: '5678',
  }]);
  if (success) {
    console.log('向记录中更新了两个部门');
  } else {
    console.log('记录更新失败');
  }
}

```
```typescript
// 设置记录的部门值
const departmentField = sheet.getField('部门');
if (Base.isFieldOfType(departmentField, 'department')) {
  const success = await departmentField.setValueAsync('rec123456', [{
    deptId: '1234',
  }, {
    deptId: '5678',
  }]);
  if (success) {
    Output.log('向记录中更新了两个部门');
  } else {
    Output.log('记录更新失败');
  }
}

```