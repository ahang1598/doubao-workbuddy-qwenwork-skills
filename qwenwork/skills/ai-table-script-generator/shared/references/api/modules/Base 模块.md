# Base 模块

当前AI表格格实例，AI表格格相关 API 的主入口，提供了操作AI表格基础对象的方法，支持查询权限、管理数据表以及获取选择区域等信息。

```typescript
const base = DingdocsScript.base;
```
```typescript
const base = Base; // 提供了全局变量Base
```
> 文中未声明的类型定义，请至[请至钉钉文档查看附件《AI表格JSAPI 类型描述》](../interface/API%20类型定义.md)中进行查询

### getActiveSheet

获取当前激活的数据表对象。

```typescript
getActiveSheet(): Sheet | null
```

**返回值**

*   [`Sheet[] | null`](../modules/Sheet%20模块.md) - 当前选中的数据表对象，若未选中任何数据表则返回 null
    

**示例**

```typescript
const activeSheet = base.getActiveSheet();
if (activeSheet) {
  console.log(`当前选中的数据表: ${activeSheet.getName()}`);
} else {
  console.log('当前未选中任何数据表');
}

```
```typescript
const activeSheet = Base.getActiveSheet();
if (activeSheet) {
  Output.log(`当前选中的数据表: ${activeSheet.getName()}`);
} else {
  Output.log('当前未选中任何数据表');
}

```

### getSheet

根据数据表ID或数据表名称获取指定数据表。

```typescript
getSheet(idOrName: string): Sheet | null

```

**参数**

*   `idOrName`: `string` - 数据表ID或数据表名称
    

**返回值**

*   [`Sheet | null`](../modules/Sheet%20模块.md) - 匹配的数据表对象，若未找到则返回 null
    

**示例**

```typescript
// 通过名称获取数据表
const productSheet = base.getSheet('产品清单');
if (productSheet) {
  console.log(`成功获取数据表，字段数量: ${productSheet.getFields().length}`);
}

// 通过ID获取数据表
const sheetById = base.getSheet('sht123456');

```
```typescript
// 通过名称获取数据表
const productSheet = Base.getSheet('产品清单');
if (productSheet) {
  Output.log(`成功获取数据表，字段数量: ${productSheet.getFields().length}`);
}

// 通过ID获取数据表
const sheetById = Base.getSheet('sht123456');

```

### getSheets

获取当前用户可见的所有数据表。

```typescript
getSheets(): Sheet[]
```

**返回值**

*   [`Sheet[]`](../modules/Sheet%20模块.md) - 当前用户可见的所有数据表对象数组
    

**示例**

```typescript
const allSheets = base.getSheets();
console.log(`可见的数据表数量: ${allSheets.length}`);
allSheets.forEach(sheet => {
  console.log(`- ${sheet.getName()}`);
});

```
```typescript
const allSheets = Base.getSheets();
Output.log(`可见的数据表数量: ${allSheets.length}`);
allSheets.forEach(sheet => {
  Output.log(`- ${sheet.getName()}`);
});

```

### insertSheet

插入一张数据表。

```typescript
insertSheet(name: string, fields?: FieldToInsert[]): Sheet

```

**参数**

*   `name`: `string` - 数据表名称
    
*   `fields`: [`FieldToInsert[]`](../interface/API%20类型定义.md)  (可选) - 数据表携带的字段配置，不传时会携带默认空数据表模版的字段
    

根据字段类型不同，支持传入的字段属性结构也不同，具体可以参考[《字段数据结构》](../interface/字段类型结构.md)

**返回值**

*   [`Sheet`](../modules/Sheet%20模块.md) - 新插入的数据表对象
    

**示例**

```typescript
// 创建一个仅有默认字段的数据表
const newSheet = base.insertSheet('新数据表');

// 创建一个带有自定义字段的数据表
const customSheet = base.insertSheet('客户信息', [
  { name: '客户名称', type: 'text' },
  { name: '注册日期', type: 'date' }
]);

```
```typescript
// 创建一个仅有默认字段的数据表
const newSheet = Base.insertSheet('新数据表');

// 创建一个带有自定义字段的数据表
const customSheet = Base.insertSheet('客户信息', [
  { name: '客户名称', type: 'text' },
  { name: '注册日期', type: 'date' }
]);

```

### updateSheet

根据数据表ID更新指定数据表。

```typescript
updateSheet(id: string, sheetConfig: SheetToUpdate): Sheet

```

**参数**

*   `id`: `string` - 数据表ID
    
*   `sheetConfig`: [`SheetToUpdate`](../interface/API%20类型定义.md) - 需要更新的数据表名称和描述
    

**返回值**

*   [`Sheet`](../modules/Sheet%20模块.md) - 更新的数据表对象，支持链式调用
    

### deleteSheet

根据数据表ID或数据表名称删除指定数据表。

```typescript
deleteSheet(idOrName: string): Base

```

**参数**

*   `idOrName`: `string` - 数据表ID或数据表名称
    

**返回值**

*   `Base` - Base对象本身，支持链式调用
    

**示例**

```typescript
// 通过名称删除数据表
base.deleteSheet('临时数据表');

// 通过ID删除数据表并链式调用
base.deleteSheet('sht123456').getSheets();

```

### isFieldOfType

判断字段是否为指定字段类型

```typescript
isFieldOfType: <T extends FieldType>(field: Field<FieldType>, type: T) => field is Field<T>;
```

**参数**

*   `field`: [`Field`](../modules/Field%20模块.md) - 需要判断类型的字段对象
    
*   `field`: [`FieldType`](../interface/API%20类型定义.md) - 指定字段类型
    

**返回值**

*   `boolean` - 是否为对应类型的字段
    

**示例**

```typescript
const field = sheet.getField('数字');
if (field && base.isFieldOfType(field, 'number')) {
    console.log('This is a number field');
} else {
    console.log('This is not a number Field')
}
```
```typescript
const field = sheet.getField('数字');
if (field && Base.isFieldOfType(field, 'number')) {
    Output.log('This is a number field');
} else {
    Output.log('This is not a number Field')
}
```

### getSelection

获取当前AI表格激活区域的信息

```typescript
getSelection: () => Selection;

```

**返回值**

*    [`Selection`](../interface/API%20类型定义.md) - 数据表激活区域的信息
    

### getDentryUuid

获取文档dentryUuid。

```typescript
getDentryUuid(): string
```

**返回值**

*   `string` - 文档的dentryUuid
    

**示例**

```typescript
const uuid = base.getDentryUuid();
console.log(`当前文档UUID: ${uuid}`);

```
```typescript
const uuid = Base.getDentryUuid();
Output.log(`当前文档UUID: ${uuid}`);

```

### getPermissionAsync

获取文档权限。

```javascript
getPermissionAsync: (params: IGetPermission) => Promise<boolean>;
```

**参数**

*    [`IGetPermission`](../interface/API%20类型定义.md) **-** 权限范围
    

**返回值**

*   `Promise<boolean>` - 是否拥有权限
    

示例

```typescript
const hasPermission = await base.getPermissionAsync({
    scope: PermissionScope.BASE,
    permissionType: PermissionType.MANAGE,
});
console.log('当前', hasPermission ? '拥有' : '未拥有', 'AI 表格管理权限')
```
```typescript
const hasPermission = await Base.getPermissionAsync({
    scope: PermissionScope.BASE,
    permissionType: PermissionType.MANAGE,
});
Output.log('当前', hasPermission ? '拥有' : '未拥有', 'AI 表格管理权限')
```

## 注意事项

1.  在使用 `insertSheet` 方法时，确保提供的字段名称不重复，且第一个字段类型必须支持作为主字段
    
2.  不能删除最后一张数据表，调用 `deleteSheet` 时需注意
    
3.  部分操作受权限限制，在执行前可以通过 `getPermissionAsync` 检查权限