### 类型名称：Selection
### 类型定义
```typescript
interface Selection {
  /** 当前AI表格的ID */
  baseId: string;
  /** 当前选中区域所属数据表ID，未选中数据表时返回null */
  sheetId: SheetId | null;
  /** 当前选中区域所属视图ID，未选中视图时返回null */
  viewId: string | null;
  /** 当前选中区域所属字段ID，未选中单元格时返回null */
  fieldId: FieldId | null;
  /** 当前选中区域所属记录ID，未选中单元格时返回null */
  recordId: string | null;
  /**
   * 当前选中表区域的范围
   */
  selectedArea: {
    /**
     * 当前选中区域所属字段ID
     */
    fieldIds: string[] | null;
    /**
     * 当前选中区域内记录ID列表。
     * 大数据表下如果选中了整列，不会返回所有记录ID，需通过 selectedAllRows 判断
     */
    recordIds: string[] | null;
    /**
     * 是否选中当前视图下所有记录
     */
    selectedAllRows: boolean;
  } | null;
}
```

### 类型名称：NumericalFormatter
### 类型定义
```typescript
type NumericalFormatter =
  "INT" /** 整数 */ |
  "FLOAT_1" /** 保留1位小数 */ |
  "FLOAT_2" /** 保留2位小数 */ |
  "FLOAT_3" /** 保留3位小数 */ |
  "FLOAT_4" /** 保留4位小数 */ |
  "FLOAT_5" /** 保留5位小数 */ |
  "FLOAT_6" /** 保留6位小数 */ |
  "FLOAT_7" /** 保留7位小数 */ |
  "FLOAT_8" /** 保留8位小数 */ |
  "FLOAT_9" /** 保留9位小数 */ |
  "THOUSAND" /** 开启千分位 */ |
  "THOUSAND_FLOAT" /** 开启千分位，并保留两位小数 */ |
  "PERCENT" /** 百分比整数 */ |
  "PERCENT_FLOAT" /** 百分比，并保留两位小数 */;
```

### 类型名称：CurrencyFormatter
### 类型定义
```typescript
type CurrencyFormatter =
  "INT" /** 整数 */ |
  "FLOAT_1" /** 保留1位小数 */ |
  "FLOAT_2" /** 保留2位小数 */ |
  "FLOAT_3" /** 保留3位小数 */ |
  "FLOAT_4" /** 保留4位小数 */;
```

### 类型名称：DateFormatter
### 类型定义
```typescript
type DateFormatter =
  "YYYY-MM-DD" |
  "YYYY-MM-DD HH:mm" |
  "YYYY-MM-DD HH:mm:ss" |
  "YYYY/MM/DD" |
  "YYYY/MM/DD HH:mm" |
  "YYYY/MM/DD HH:mm:ss" |
  "YYYY年MM月" |
  "MM月DD日" |
  "YYYY年MM月DD日";
```

### 类型名称：ProgressFormatter
### 类型定义
```typescript
type ProgressFormatter =
  "PERCENT" /** 百分比整数 */ |
  "NUMBER" /** 数值整数 */ |
  "NUMBER_FLOAT_1" /** 数值，保留1位小数 */ |
  "NUMBER_FLOAT_2" /** 数值，保留2位小数 */ |
  "NUMBER_FLOAT_3" /** 数值，保留3位小数 */ |
  "PERCENT_FLOAT_1" /** 百分比，保留1位小数 */ |
  "PERCENT_FLOAT_2" /** 百分比，保留1位小数 */ |
  "PERCENT_FLOAT_3" /** 百分比，保留1位小数 */;
```

### 类型名称：SelectOption
### 类型定义
```typescript
interface SelectOption {
  /** 选项id(由系统默认生成，创建选项时无需传入此项) */
  id?: string;
  /** 选项名称 */
  name: string;
}
```

### 类型名称：ISelectFieldOption
### 类型定义
```typescript
interface ISelectFieldOption {
  /** 选项ID */
  id: string;
  /** 选项名称 */
  name: string;
  /** 选项颜色 */
  color?: string;
}
```

### 类型名称：IOptionConfig
### 类型定义
```typescript
type IOptionConfig = {
  /** 需要更新的选项名称（可选） */
  name?: string;
};
```

### 类型名称：RatingIconType
### 类型定义
```typescript
type RatingIconType =
  "star" |
  "nps" |
  "heart" |
  "like" |
  "fire" |
  "emoji" |
  "lighting" |
  "flower" |
  "flash";
```

### 类型名称：CurrencyType
### 类型定义
```typescript
type CurrencyType =
  "CNY" | "HKD" | "USD" | "EUR" | "JPY" |
  "GBP" | "MOP" | "VND" | "KRW" | "AED" |
  "AUD" | "BRL" | "CAD" | "CHF" | "INR" |
  "IDR" | "MXN" | "MYR" | "PHP" | "PLN" |
  "RUB" | "SGD" | "THB" | "TRY" | "TWD";
```

### 类型名称：IOpenFile
### 类型定义
```typescript
interface IOpenFile {
  /** 文件名 */
  name: string;
  /** 文件MIME类型 */
  type: string;
  /** 文件大小（字节） */
  size: number;
  /** 文件内容，可以是base64编码的字符串或ArrayBuffer */
  content: string | ArrayBuffer;
}
```

### 类型名称：UserCellValue
### 类型定义
```typescript
type UserCellValue = {
  /** 用户uid，读取人员字段时可能返回 */
  uid?: string;
  /** 用户userId，支持写入人员字段时传入 */
  userId?: string;
  /** 用户unionId，支持写入人员字段时传入和读取人员字段时返回 */
  unionId?: string;
  /** 用户uid 密文 */
  uidCipher?: string;
  /** 员工工号，支持写入人员字段时传入 */
  jobNumber?: string;
  /** 外部联系人ID，支持写入人员字段时传入 */
  extContactUserId?: string;
  /** 用户名，读取人员字段时返回 */
  name?: string;
  /** 是否为外部用户 */
  isOuter?: boolean;
}
```

> 人员字段的单元格值是 `UsersCellValue = UserCellValue[]`。

### 类型名称：GroupCellValue
### 类型定义
```typescript
interface GroupCellValue {
  /** 群会话ID */
  openConversationId?: string;
  /** 群会话名称 */
  name?: string;
}
```

### 类型名称：DepartmentCellValue
### 类型定义
```typescript
type DepartmentCellValue = {
  /** 部门ID */
  deptId: string;
  /** 部门名称 */
  name?: string;
}
```

### 类型名称：SheetToUpdate
### 类型定义
```typescript
interface SheetToUpdate {
  /** 需要更新的表格名称 */
  name?: string;
  /** 需要更新的数据表描述 */
  desc?: string;
}
```

### 类型名称：FieldType
### 类型定义
```typescript
type FieldType =
  'text' /** 文本 */ |
  'number' /** 数字 */ |
  'singleSelect' /** 单选 */ |
  'multipleSelect' /** 多选 */ |
  'date' /** 日期 */ |
  'checkbox' /** 复选框 */ |
  'user' /** 人员 */ |
  'group' /** 群组 */ |
  'department' /** 部门 */ |
  'unidirectionalLink' /** 单向关联 */ |
  'bidirectionalLink' /** 双向关联 */ |
  'attachment' /** 附件 */ |
  'url' /** 链接 */ |
  'createdTime' /** 创建时间 */ |
  'lastModifiedTime' /** 更新时间 */ |
  'creator' /** 创建人 */ |
  'lastModifier' /** 最后更新人 */ |
  'rating' /** 评分 */ |
  'progress' /** 进度 */ |
  'currency' /** 货币 */ |
  'telephone' /** 电话 */ |
  'email' /** 邮箱 */ |
  'idCard' /** 身份证 */ |
  'barcode' /** 条形码 */ |
  'primaryDoc' /** 文档 */ |
  'richText' /** 富文本 */ |
  'geolocation' /** 地理位置 */ |
  'autoNumber' /** 自动编号 */ |
  'formula' /** 公式 */ |
  'lookup' /** 关联引用 */ |
  'filterUp' /** 查找引用 */ |
  'object' /** 对象 */ |
  'button' /** 按钮 */ |
  'flow' /** 流程 */;
```

> ⚠️ 常见错误：`multiSelect`、`updatedTime` 是**模型层内部名**，对外 API 必须用 `multipleSelect`、`lastModifiedTime`。另外不存在 `FieldType` 枚举对象，只能传字符串字面量。

### 类型名称：FieldProperty
### 类型定义
```typescript
interface FieldProperty {
  /** 数据格式 */
  formatter?: NumberFormatter | DateFormatter | ProgressFormatter;

  /** 单选、多选选项配置 */
  choices?: SelectOption[];

  /** 单向、双向关联字段关联数据表Id */
  linkedSheetId?: string;

  /** 是否支持多选 */
  multiple?: boolean;

  /** 最小值（适用于进度、评分字段） */
  min?: number;
  /** 最大值（适用于进度、评分字段） */
  max?: number;

  /** 是否自定义进度条值 */
  customizeRange?: boolean;

  /** 评分字段图标 */
  icon?: RatingIconType;

  /** 货币币种 */
  currencyType?: CurrencyType;

  /** 公式字段配置 */
  formula?: string;
}
```

### 类型名称：FieldToInsert
### 类型定义
```typescript
interface FieldToInsert {
  /** 字段名称 */
  name: string;
  /** 字段类型 */
  type: FieldType;
  /** 字段属性 */
  property?: FieldProperty;
}
```

### 类型名称：FieldToUpdate
### 类型定义
```typescript
interface FieldToUpdate {
  /** 字段名称 */
  name?: string;
  /** 字段类型 */
  type?: FieldType;
  /** 字段属性 */
  property?: FieldProperty;
  /** 字段描述 */
  desc?: string;
}
```

### 类型名称：FieldToUpdateWithoutType
### 类型定义
```typescript
interface FieldToUpdateWithoutType {
  /** 字段ID(可选), 不存在时则根据字段名称查找指定字段 */
  id?: string;
  /** 字段名称(可选)，当不传入字段ID时将根据名称查询需要更新的字段，当传入字段ID时将把当前名称设置给ID对应的字段 */
  name?: string;
  /** 字段属性(可选) */
  property?: FieldProperty;
  /** 字段描述(可选) */
  desc?: string;
}
```

### 类型名称：GetRecordsOptions
### 类型定义
```typescript
interface GetRecordsOptions {
  /** （可选）指定要加载的记录ID列表 */
  recordIds?: string[];
  /** （可选）指定要加载的字段ID列表 */
  fieldIds?: string[];
  /** （可选）指定要加载的字段ID或字段名列表（会自动解析为 fieldIds） */
  fieldIdOrNames?: string[];
  /** （可选）指定每次分页加载记录量。脚本/边栏插件下默认 500，取值范围 1~500 */
  pageSize?: number;
  /** （可选）用于分页的游标，当从头开始查询时可不传此项 */
  cursor?: string;
  /** （可选）筛选条件，见下方 Filter */
  filter?: Filter;
  /** （可选）指定要加载记录的视图来源 */
  viewId?: string;
}
```

### 类型名称：Filter（getRecordsAsync 专用）
### 类型定义
```typescript
/**
 * ⚠️ 这套类型只用于 sheet.getRecordsAsync({ filter })，
 * 与 GridView 的 IFilterInfo / FilterInfoCondition（conjunction / fieldId / 'is'）完全不同，不能混用。
 */
interface Filter {
  /** 条件组合形式，默认 'and' */
  combination?: 'and' | 'or';
  /** 条件列表 */
  conditions: Condition[];
}

interface Condition {
  /** 字段ID或字段名 */
  field: string;
  /** 条件运算符 */
  operator: ConditionOperator;
  /** 条件值，注意是【数组】；empty / notEmpty 时可不传 */
  value?: Array<string | boolean | number | object>;
}

type ConditionOperator =
  'equal' | 'notEqual' | 'greater' | 'greaterEqual' | 'less' | 'lessEqual' |
  'contain' | 'notContain' | 'empty' | 'notEmpty';
```

### 类型名称：GetRecordsResult
### 类型定义
```typescript
interface GetRecordsResult {
  /* 是否还有其他记录尚未加载 */
  hasMore: boolean;
  /* 游标 */
  cursor?: string;
  /* 返回的记录 */
  records: Record[];
  /* 总行数 */
  total?: number;
}
```

### 类型名称：RecordToInsert
### 类型定义
```typescript
interface RecordToInsert {
  /**
   * 需要插入的字段
   */
  fields: Record<string /* fieldId 字段ID */, CellValue /** 字段值 */>;
}
```

### 类型名称：RecordToUpdate
### 类型定义
```typescript
interface RecordToUpdate {
  /**
   * 需要更新的字段
   */
  fields: Record<string /* 字段ID */, CellValue /** 字段值 */>;
  /** 记录ID */
  id: string;
}
```

### 类型名称：ViewType
### 类型定义
```typescript
type ViewType =
  'Grid' /** 表格视图 */ |
  'Kanban' /** 看板视图 */ |
  'Gallery' /** 画册视图 */ |
  'Gantt' /** 甘特视图 */ |
  'Calendar' /** 日历视图 */ |
  'Form' /** 表单视图 */ |
  'List' /** 列表视图 */;
```

### 类型名称：ViewToInsert
### 类型定义
```typescript
interface ViewToInsert {
  /** 视图名称 */
  name: string;
  /** 视图类型 */
  type: ViewType;
  /** 视图描述 */
  desc?: string;
}
```

### 类型名称：ViewToUpdate
### 类型定义
```typescript
interface ViewToUpdate {
  /** 视图名称 */
  name?: string;
  /** 视图描述 */
  desc?: string;
}
```

### 类型名称：FieldWidths
### 类型定义
```typescript
type FieldWidths = Record<string /** fieldId */, number /** width */>;
```

### 类型名称：FilterOperator
### 类型定义
```typescript
enum FilterOperator {
  Is = 'is',                    // 等于
  IsNot = 'isNot',             // 不等于
  Contains = 'contains',        // 包含
  DoesNotContain = 'doesNotContain',  // 不包含
  IsEmpty = 'isEmpty',         // 为空
  IsNotEmpty = 'isNotEmpty',   // 不为空
  IsGreater = 'isGreater',     // 大于
  IsGreaterEqual = 'isGreaterEqual',  // 大于或等于
  IsLess = 'isLess',           // 小于
  IsLessEqual = 'isLessEqual'  // 小于或等于
}
```

### 类型名称：FilterInfoCondition
### 类型定义
```typescript
interface FilterInfoCondition {
  /** 字段ID */
  fieldId: string;
  /** 条件ID（可选） */
  conditionId?: string;
  /** 匹配值 */
  value: any;
  /** 操作符 */
  operator: FilterOperator;
}
```

### 类型名称：FilterConjunction
### 类型定义
```typescript
enum FilterConjunction {
  And = 'and',  // 满足所有条件
  Or = 'or'     // 满足任一条件
}
```

### 类型名称：IFilterInfo
### 类型定义
```typescript
interface IFilterInfo {
  /** 筛选条件之间的关系 */
  conjunction: FilterConjunction;
  /** 具体的筛选条件 */
  conditions: FilterInfoCondition[];
}
```

### 类型名称：IGridViewMeta
### 类型定义
```typescript
interface IGridViewMeta {
  /** 视图ID */
  id: string;
  /** 视图名称 */
  name: string;
  /** 视图类型 */
  type: 'Grid';
  /** 视图配置 */
  property: {
    /** 父子记录配置 */
    hierarchyConfig: {
      /** 父记录字段ID */
      fieldId?: string;
    };
    /** 筛选规则 */
    filterInfo: IFilterInfo | null;
  };
}
```

### 类型名称：IAddFilterConditionParams
### 类型定义
```typescript
type IAddFilterConditionParams = FilterInfoCondition | FilterInfoCondition[];
```

### 类型名称：IUpdateFilterConditionParams
### 类型定义
```typescript
type IUpdateFilterConditionParams = FilterInfoCondition | FilterInfoCondition[];
```

### 类型名称：FillColorType
### 类型定义
```typescript
enum FillColorType {
  /** 单元格填色 */
  Cell = 'cell',
  /** 行填色 */
  Row = 'row',
  /** 列填色 */
  Column = 'column',
  /** 行头填色 */
  PreRow = 'preRow',
}
```

### 类型名称：FillColorCode
### 类型定义
```typescript
/**
 * 填色颜色代码类型
 * 对应系统预定义的颜色索引，如 "0", "1", "2" 等
 */
type FillColorCode = string;
```

### 类型名称：IFillColorRule
### 类型定义
```typescript
interface IFillColorRule {
  /** 规则ID，用于唯一标识规则 */
  id: string;
  /** 填色类型 */
  type: FillColorType;
  /** 应用填色的字段ID */
  fieldId: string;
  /** 填色配置 */
  format: {
    /** 颜色代码，对应系统预定义的颜色索引（如 "0", "1", "2" 等） */
    color: FillColorCode;
  };
  /** 筛选条件（列填色时为空） */
  condition?: FilterInfoCondition;
}
```

### 类型名称：IFillColorInfo
### 类型定义
```typescript
interface IFillColorInfo {
  /** 填色规则列表 */
  rules: IFillColorRule[];
}
```

### 类型名称：IAddFillColorRuleParams
### 类型定义
```typescript
interface IAddFillColorRuleParams {
  /** 填色类型 */
  type: FillColorType;
  /** 应用填色的字段ID */
  fieldId: string;
  /** 填色配置 */
  format: {
    /** 颜色代码，对应系统预定义的颜色索引（如 "0", "1", "2" 等） */
    color: FillColorCode;
  };
  /** 筛选条件（列填色时可选） */
  condition?: FilterInfoCondition;
}
```

### 类型名称：IUpdateFillColorRuleParams
### 类型定义
```typescript
interface IUpdateFillColorRuleParams {
  /** 规则ID */
  ruleId: string;
  /** 填色类型（可选） */
  type?: FillColorType;
  /** 应用填色的字段ID（可选） */
  fieldId?: string;
  /** 填色配置（可选） */
  format?: {
    /** 颜色代码，对应系统预定义的颜色索引（如 "0", "1", "2" 等） */
    color?: FillColorCode;
  };
  /** 筛选条件（可选） */
  condition?: FilterInfoCondition;
}
```

### 类型名称：GetFieldValuesOptions
### 类型定义
```typescript
interface GetFieldValuesOptions {
  /** 要加载的recordId */
  recordIds?: string[];
  /** 分片加载数据量 */
  pageSize?: number;
  /** 游标 */
  cursor?: string;
  /** (可选)视图ID */
  viewId?: string;
}
```

### 类型名称：PagedFieldValues
### 类型定义
```typescript
interface PagedFieldValues<T extends FieldType> {
  fieldValues: Array<{
    recordId: string;
    value: CellValue | null;
  }>;
  hasMore: boolean;
  cursor?: string;
  total?: number;
  cellValues?: Array<CellValue | null>;
}
```

### 类型名称：CellValue
### 类型定义
```typescript
type CellValue =
  string | boolean | number |
  SingleSelectCellValue |
  MultiSelectCellValue |
  AssociationsValue |
  AttachmentValue |
  RichTextValue |
  LinkValue |
  null;
```

### 类型名称：SingleSelectCellValue
### 类型定义
```typescript
type SingleSelectCellValue = {
  /** 选项ID */
  id: string;
  /** 选项名称 */
  name: string;
};
```

### 类型名称：MultiSelectCellValue
### 类型定义
```typescript
type MultiSelectCellValue = SingleSelectCellValue[];
```

### 类型名称：DateCellValue
### 类型定义
```typescript
type DateCellValue = number;
```

### 类型名称：AssociationsValue
### 类型定义
```typescript
type AssociationsValue = {
  /** 关联记录的记录ID */
  linkedRecordIds: string[];
};
```

### 类型名称：AttachmentValue
### 类型定义
```typescript
/**
 * 注意：AttachmentValue 描述的是【单个附件】。
 * 附件字段的单元格值是 AttachmentValue[]，
 * 所以 attachmentField.getValueAsync() 返回 Promise<AttachmentValue[] | null>。
 */
type AttachmentValue = {
  /** 附件MIME类型 */
  type: string;
  /** 附件名称 */
  filename: string;
  /** 附件链接 */
  url: string;
  /** 缩略图URL（可选） */
  thumbUrl?: string;
  /** 附件大小（当附件为钉钉文档时，没有此属性） */
  size?: number;
  /** 附件资源ID（当附件为钉钉文档时，没有此属性） */
  resourceId?: string;
  /** 是否是钉钉文档链接 */
  isLink?: boolean;
};
```

### 类型名称：RichTextValue
### 类型定义
```typescript
type RichTextValue = {
  /** 富文本（markdown格式） */
  markdown: string;
};
```

### 类型名称：LinkValue
### 类型定义
```typescript
type LinkValue = {
  /** 链接地址 */
  link: string;
  /** 链接文字 */
  text?: string;
};
```

### 类型名称：FormulaValue
### 类型定义
```typescript
type FormulaValue = CellValue | CellValue[];
```

### 类型名称：IGetCellValuesOptions
### 类型定义
```typescript
interface IGetCellValuesOptions {
  /** 是否使用字段ID作为返回对象的键 */
  returnFieldsById?: boolean;
}
```

### 类型名称：IGetPermission
### 类型定义
```typescript
type IGetPermission = IBasePermission | ISheetPermission;

export interface IBasePermission {
  /** 权限范围 */
  scope: PermissionScope.BASE;
  /** 权限类型 */
  permissionType: PermissionType.EDIT | PermissionType.MANAGE;
}

export interface ISheetPermission {
  /** 权限范围 */
  scope: PermissionScope.SHEET;
  /** 权限类型 */
  permissionType: PermissionType.READ | PermissionType.CREATE | PermissionType.UPDATE | PermissionType.DELETE;
  /** 其它参数 */
  params: {
    /** 需要查询权限的数据表ID */
    sheetId: string;
  };
}
```

### 类型名称：PermissionScope
### 类型定义
```typescript
enum PermissionScope {
  // AI表格级
  BASE = 'base',
  // 数据表级
  SHEET = 'sheet',
  // 视图级
  VIEW = 'view',
  // 字段级
  FIELD = 'field',
  // 记录级
  RECORD = 'record',
  // 单元格级
  CELL = 'cell',
}
```

### 类型名称：PermissionType
### 类型定义
```typescript
enum PermissionType {
  /** 可编辑权限 */
  EDIT = 'edit',
  /** 可管理权限 */
  MANAGE = 'manage',
  /** 可读权限 */
  READ = 'read',
  /** 可创建权限 */
  CREATE = 'create',
  /** 可更新权限 */
  UPDATE = 'update',
  /** 可删除权限 */
  DELETE = 'delete',
  /** 可复制权限 */
  COPY = 'copy',
  /** 可分组权限 */
  GROUP = 'group',
  /** 可排序权限 */
  SORT = 'sort',
  /** 可筛选权限 */
  FILTER = 'filter',
  /** 可填色权限 */
  FILL_COLOR = 'fillColor',
}
```

### 类型名称：GeoLocationValue
### 类型定义
```typescript
type GeoLocationValue = {
  /** address */
  address: string;
  /** 简短地址 */
  name: string;
  /** 完整地址 */
  fullAddress: string;
  /** 经纬度 */
  location: [number, number];
};
```

### 类型名称：ToastOptions
### 类型定义
```typescript
interface ToastOptions {
  /** toast提示类型 */
  type: ToastType;
  /** toast内容 */
  message: string;
  /** 是否提供手动关闭消息按钮，（当消息常驻时固定为true） */
  closeable?: boolean;
  /** 手动关闭消息的回调 */
  onClose?: () => void;
  /** 消息显示持续时间。默认为short模式持续 3s, 选择long或存在行动点时持续时间为 5s,选择always时常驻在页面中。 */
  keepAlive?: 'always' | 'short' | 'long';
}
```

### 类型名称：ToastType
### 类型定义
```typescript
enum ToastType {
  /** 成功 */
  SUCCESS = 'success',
  /** 失败 */
  ERROR = 'error',
  /** 警告 */
  WARNING = 'warning',
  /** 提示 */
  INFO = 'info',
}
```