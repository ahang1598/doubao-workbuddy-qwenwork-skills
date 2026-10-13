# Output 模块

支持在运行页面中展示丰富的数据信息，类似于Console API。

### log

在运行插件面板打印文本信息，背景色为透明色，一般用于输出提示信息。

```typescript
log: (message: any) => void;
```

**参数**
- `message`: `any` - 需要打印的信息

**示例**
```typescript
Output.log('日志信息');
```

### info

在运行插件面板打印文本信息，背景色为蓝色，一般用于输出提示信息。

```typescript
info: (message: any) => void;
```

**参数**
- `message`: `any` - 需要打印的提示

**示例**
```typescript
Output.info('提示信息');
```

### success

在运行插件面板打印文本信息，背景色为绿色，一般用于输出成功信息。

```typescript
success: (message: any) => void;
```

**参数**
- `message`: `unknown` - 需要打印的信息，支持传入多个参数

**示例**
```typescript
Output.success('操作成功！共处理了 10 条记录');
```

### warn

在运行插件面板打印文本信息，背景色为黄色，一般用于输出警告信息。

```typescript
warn: (message: any) => void;
```

**参数**
- `message`: `any` - 需要打印的提示

**示例**
```typescript
Output.warn('告警信息');
```

### error

在运行插件面板打印文本信息，背景色为红色，一般用于输出错误信息。

```typescript
error: (message: any) => void;
```

**参数**
- `message`: `any` - 需要打印的提示

**示例**
```typescript
Output.error('错误信息');
```

### markdown

在运行插件面板中打印富文本内容，支持标准的markdown语法。

```typescript
markdown: (message: string) => void;
```

**参数**
- `message`: `string` - 标准markdown规范的字符串

**示例**
```typescript
Output.markdown(`## Document Title

## Section 1: Introduction

This is an introductory paragraph. Markdown allows for easy formatting of text.

### Sub-section 1.1: Features

-   **Bold text** using double asterisks or double underscores.
-   *Italic text* using single asterisks or single underscores.
-   \`Inline code\` using backticks.

## Section 2: Code Example

Here is an example of a code block:

\`\`\`python
def hello_world():
    print("Hello, Markdown!")`);
```

### table

在运行插件面板中以表格形式展示数组或对象。

```typescript
table: (data: unknown) => void
```

**参数**
- `data`: `unknown` - 通常为可序列化的数组或对象

**示例**
```typescript
Output.table([
  { name: 'John', age: 15, gender: 'Male' },
  { name: 'Alice', age: 24, gender: 'Female' },
  { name: 'Bob', age: 22, gender: 'Male' },
]);
```

### clear

清空运行插件面板中的所有输出内容。

```typescript
clear: () => void;
```

**示例**
```typescript
Output.log('这条信息会被清除');
Output.clear();
Output.log('面板已清空，这是新的输出');
```
