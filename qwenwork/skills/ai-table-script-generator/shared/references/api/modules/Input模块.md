# Input 模块

支持在运行页面中创建交互式UI，等待用户输入后执行后续步骤。每个交互式输入法都是异步的，因此调用此API时需要使用`await`表达式。

### textAsync

在运行插件面板插入一个输入框，等待用户输入完毕后执行后续操作。

```typescript
textAsync: (label: string, config?: InputConfig<string>) => Promise<string>;
```

**参数**
- `label`: `string` - 输入框标题
- `config`: `InputConfig<string>` - 配置参数，详细见后文

**返回值**
- `Promise<string>` - 用户输入并提交后返回的输入结果

**示例**
```typescript
const userInput = await Input.textAsync("请输入一段内容");
Output.info('用户输入的内容为', userInput);
```

### selectAsync

在运行插件面板插入一个选择器，显示一组按钮，等待用户点击后执行后续操作。

```typescript
selectAsync: <V = unknown>(label: string, options: Array<string | SelectOption<V>>, config: InputConfig<string | V | undefined>) => Promise<string | V | undefined>;

interface SelectOption<V> {
  /** 选项展示的文本 */
  text: string;
  /** 选项值 */
  value: V;
}
```

**参数**
- `label`: `string` - 选择器标题
- `options`: `Array<string | SelectOption>`选项配置，支持设置字符串格式的选项，或同时配置选项的文案和实际值。
- `config`: `InputConfig<string | V | undefined>` - 配置参数，详细见后文

**返回值**
- `Promise<string | V | undefined>` - 用户点击按钮后返回的结果

**示例**
```typescript
const userInput = await Input.selectAsync('请选择答案', ['A', 'B', 'C', 'D']);
Output.info('用户选择的答案为', userInput);
```

### formAsync

在运行面板中插入一个表单，等待用户提交后执行后续操作

```typescript
formAsync: (title: string, items: FormItem[], config?: InputConfig<Record<FormItemKey, FormItemResult | undefined>>) => Promise<Record<FormItemKey, FormItemResult | undefined>>;

/** 表单项的唯一标识 */
type FormItemKey = string;

type FormItem = {
  /** 表单项唯一标识 */
  key: FormItemKey;
  /** 表单项是否为必填项，默认为 true */
  required?: boolean;
} & (
  | SheetFormItem
  | FieldFormItem
  | ViewFormItem
  | RecordFormItem
  | TextFormItem
  | NumberFormItem
  | SelectFormItem
);

/** 数据表表单项 */
interface SheetFormItem {
  type: 'sheet';
  option: {
    /** 表单项的标题（可选，为空时默认以 key 作为标题） */
    label?: string;
    /** 表单项的描述说明（可选） */
    description?: string;
  };
}

/** 字段表单项 */
interface FieldFormItem {
  type: 'field';
  option: {
    label?: string;
    description?: string;
    /** 字段所属的数据表表单项唯一标识 */
    referenceSheet: FormItemKey;
  };
}

/** 视图表单项 */
interface ViewFormItem {
  type: 'view';
  option: {
    label?: string;
    description?: string;
    /** 视图所属的数据表表单项唯一标识 */
    referenceSheet: FormItemKey;
  };
}

/** 记录表单项 */
interface RecordFormItem {
  type: 'record';
  option: {
    label?: string;
    description?: string;
    /** 记录所属的数据表表单项唯一标识 */
    referenceSheet: FormItemKey;
  };
}

/** 文本输入框表单项 */
interface TextFormItem {
  type: 'text';
  option: {
    label?: string;
    description?: string;
  };
}

/** 数字输入框表单项 */
interface NumberFormItem {
  type: 'number';
  option: {
    label?: string;
    description?: string;
  };
}

/** 选择器表单项 */
interface SelectFormItem {
  type: 'select';
  option: {
    label?: string;
    description?: string;
    options: Array<string | SelectOption<unknown>>;
  };
}

type FormItemResult = 
  | Sheet      /** 数据表 */
  | Field      /** 字段 */
  | View       /** 视图 */
  | string     /** 文本输入框返回结果 */
  | number     /** 数字输入框返回结果 */
  | unknown;   /** 选择器返回结果 */
```

**参数**
- `title`: `string` - 表单标题
- `items`: `FormItem[]`表单项。
- `config`: `InputConfig<Record<FormItemKey, FormItemResult | undefined>>` - 配置参数，详细见后文

**返回值**
- `Promise<Record<FormItemKey, FormItemResult | undefined>>` - 用户点击提交后返回的结果

**示例**
```typescript
const formResult = await Input.formAsync('请填写表单', [{
    type: 'sheet',
    key: 'sheet',
    option: {
        label: '选择一张数据表',
    },
    required: true,
}, {
    type: 'field',
    key: 'field',
    option: {
        label: '选择一个字段',
        description: '字段来自于上方选择的数据表',
        referenceSheet: 'sheet',
    },
    required: false,
}, {
    type: 'text',
    key: 'text',
    option: {
        label: '请输入文本',
    },
    required: true,
}, {
    type: 'number',
    key: 'number',
    option: {
        label: '请输入数字',
    },
    required: true,
}, {
    type: 'select',
    key: 'select',
    option: {
        label: '请选择选项',
        options: ['1', '2', '3'],
    },
}]);
Output.table(formResult);
```

### 入参校验

`textAsync`、`selectAsync`、`formAsync` 均支持传入可选的 `config` 参数，用于对用户输入进行校验。校验不通过时，会在输入框下方展示错误信息，阻止用户提交，直到校验通过为止。

```typescript
interface InputConfig<T> {
  /**
   * 校验函数，接收用户输入值，返回校验结果。
   * 支持同步或异步校验。
   */
  validate?: (response: T) => ValidationResult | Promise<ValidationResult>;
}

type ValidationResult =
  | { valid: true }
  | { valid: false; error: string };
```

**示例**
```typescript
// 校验用户输入不能为空
const userInput = await Input.textAsync('请输入内容', {
  validate: (value) => {
    if (!value || value.trim() === '') {
      return { valid: false, error: '内容不能为空' };
    }
    return { valid: true };
  },
});

// 异步校验：检查输入值是否已存在
const name = await Input.textAsync('请输入名称', {
  validate: async (value) => {
    const exists = await checkNameExists(value);
    if (exists) {
      return { valid: false, error: '该名称已存在，请重新输入' };
    }
    return { valid: true };
  },
});
```

# 按钮字段触发脚本

脚本可以通过两种方式启动：
1. **直接运行**：在脚本面板中点击运行。
2. **按钮字段触发**：点击数据表中的按钮字段按钮运行。

当通过 **按钮字段** 触发脚本时，`formAsync` 方法会自动识别当前的上下文（即点击按钮所在的行记录），并尝试自动填充表单中对应的内容。

### 自动填充规则

如果 `formAsync` 的表单项满足以下条件，将会被自动填充并直接提交，无需用户手动操作：

1. **Sheet 类型** 
    - 会自动填充为当前 Button 字段所在的数据表。
2. **View 类型** 
    - 需配置 `referenceSheet` 指向上述自动填充的 Sheet 表单项。
    - 会自动填充为当前所在的视图。
3. **Record 类型** 
    - 需配置 `referenceSheet` 指向上述自动填充的 Sheet 表单项。
    - 会自动填充为当前点击 Button 的那一行记录。
    - 如果配置了 `referenceView`，则也会校验当前记录是否在该视图内。

**注意**：只有当所有 **必填 (`required: true`)** 的表单项都能在上下文中找到对应值并成功填充时，表单才会自动提交。如果任一必填项无法自动填充（例如表单中还包含一个需要用户手动输入的文本框），则表单面板会正常弹出，已识别的项会预先填入，等待用户完成剩余输入后手动提交。

通过这种机制，可以编写出既支持手动运行（用户选表选记录），又支持按钮字段快捷操作（自动定位当前记录）的通用脚本。
