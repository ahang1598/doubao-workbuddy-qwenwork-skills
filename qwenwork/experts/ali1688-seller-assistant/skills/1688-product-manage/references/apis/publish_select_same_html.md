# 批量发品 - 同款勾选 HTML

**文件名**: `publish_select_same_{timestamp}.html`（timestamp 为毫秒级时间戳）  
**生成方式**: 由 CLI 命令 `python3 cli.py product_publish --show-all-candidates` **一次性生成并自动打开**（与全部候选 markdown 同步返回）  
**输出路径**: `scripts/publish_select_same_{timestamp}.html`（CLI 返回 `data.htmlPath` 字段为该文件绝对路径）  
**用途**: 批量发品流程中，为商家提供可视化的同款勾选界面，商家勾选每张主图对应的同款商品后一键复制结果带入聊天框。

## 触发时机

在批量发品步骤 3 中商家选择了「选项 2：查看所有同款信息后再选择」后，进入步骤 4。**该步骤的「展示全部候选」与「生成 HTML」由同一条命令 `product_publish --show-all-candidates` 一次性完成**，CLI 在 `markdown` 字段中输出全部候选信息与「已为您打开网页」提示块，并在 `data.htmlPath` 中返回 HTML 绝对路径，无需 Agent 再做任何 Python 调用。

> 注意：仅在商家明确选择「查看所有同款后再选」时才触发该 CLI 命令；若商家选择「默认第一个同款」则无需生成此文件。

⛔ **Agent 严禁**：使用 `python3 -c "..."`、临时脚本或任何方式重复调用 `_generate_select_same_html`。重复调用会导致 Python 解释器二次冷启动、模块二次 import、浏览器重复弹窗等性能与体验问题。

## 输入数据格式（candidates）

`_generate_select_same_html(candidates: list)` 接收的 `candidates` 参数格式：

```json
[
    {
        "index": 1,                       // 图片序号（对应批量识图中的图片编号）
        "main_image_url": "https://...",   // 商家原始主图URL
        "same_items": [                    // 同款候选列表
            {
                "seq": 1,                  // 同款序号（组内从1递增）
                "image_url": "https://...", // 同款主图URL
                "title": "xxx",            // 同款商品标题
                "attributes": "颜色:红色 尺码:XL"  // 属性键值对
            }
        ]
    }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `index` | number | 图片序号，对应批量识图中的图片编号 |
| `main_image_url` | string | 商家原始主图 URL |
| `same_items` | array | 该图片的同款候选列表 |
| `same_items[].seq` | number | 同款序号，**组内从 1 开始递增**（非全局递增） |
| `same_items[].image_url` | string | 同款商品主图 URL |
| `same_items[].title` | string | 同款商品标题 |
| `same_items[].attributes` | string | 同款商品属性（键值对格式） |

## 表格结构

| 列名 | 类型 | 说明 |
|------|------|------|
| 勾选 | checkbox | 每行一个勾选框，默认勾选每张主图的第一个同款 |
| 序号 | 只读 | 同款候选的序号，**组内从 1 开始递增**（每张主图的同款序号独立编号） |
| 主图 | 只读/图片 | 商家上传的原始主图缩略图（80×80），一张主图对应多行同款数据（用 rowspan 合并单元格） |
| 同款主图 | 只读/图片 | 同款商品的主图缩略图（80×80） |
| 标题 | 只读 | 同款商品标题 |
| 属性 | 只读 | 同款商品属性（键值对格式，如 `颜色: 红色 / 尺寸: L`） |

> 💡 「主图」列使用 `rowspan` 将同一张主图的多个同款候选行合并为一个单元格，视觉上清晰分组。

## 交互规则

### 默认勾选

每张主图的第一个同款默认勾选（`checked`），商家可更改选择。

### 单选约束

每张主图只能勾选一个同款（同一主图分组内的 checkbox 互斥，类似 radio 行为但使用 checkbox 样式）。当商家勾选同组内的另一个候选时，同组已勾选的自动取消。

### 主图分组

通过 `data-group` 属性标识同一主图的候选行，JS 事件监听实现组内互斥逻辑。

## 交互按钮

### 全局按钮（表格上方和下方各一个，主要 CTA）

| 按钮文案 | 功能 |
|------|------|
| 📋 复制勾选同款 · 点我复制并返回继续 | 收集所有被勾选同款的信息，按指定格式拼接并复制到剪贴板；Toast 提示商家返回聊天框粘贴继续 |

## 复制到剪贴板的格式

```
图1: 同款序号{n}
图2: 同款序号{n}
图3: 同款序号{n}
...
```

示例：

```
图1: 同款序号1
图2: 同款序号3
图3: 同款序号2
```

商家复制后粘贴到聊天框，Agent 基于此内容解析每张图对应的同款选择，继续执行后续发品流程。

## 使用引导（HTML 顶部黄色提示条）

> 💡 **使用说明**：请勾选每张图片对应的同款商品，每张图片只能选一个同款。确认后点击下方按钮复制结果，回到聊天框粘贴。

## Agent 聊天框输出规范（强约束）

`product_publish --show-all-candidates` 命令的 `markdown` 字段中**已包含**全部候选展示 + 「✨ 已为您打开《批量发品 - 同款勾选》网页」提示块 + 操作引导 + 手动打开兜底 + 下一步选项。

**Agent 唯一职责**：原样输出 CLI 返回的 `markdown` 字段。

⛔ **禁止行为**：
- 删减或改写「✨ 已为您打开...」提示块、操作引导项、手动打开兜底引用
- 把网页提示与候选展示合并到自定义段落中
- 二次拼接 Python 脚本调用 `_generate_select_same_html`
- 跳过商家粘贴勾选结果环节，自行判断同款序号

CLI 已统一处理以下内容（Agent 不需要也不应该重复输出）：
1. 加粗主提示：`✨ **已为您打开《批量发品 - 同款勾选》网页**`
2. 操作引导项目符列表（默认勾选 / 单选 / 复制按钮 / 返回粘贴）
3. 手动打开兜底引用：`> 网页未自动打开？手动打开文件：scripts/publish_select_same_{timestamp}.html`
4. `---` 分隔与下一步操作选项

## 文件生命周期

- **生成时机**: 每次触发时生成新文件（带时间戳避免冲突）
- **清理策略**: 商家完成操作后可手动清理，不自动删除
- **状态独立**: HTML 仅供商家可视化勾选，不写入 `.batch_publish_state.json`，实际同款选择以商家粘贴到聊天框的内容为准

## 技术说明

- 纯前端 HTML + JavaScript，无后端依赖
- 使用 `navigator.clipboard.writeText` 实现剪贴板复制（降级为 `execCommand('copy')`）
- 生成后通过系统命令自动打开（macOS: `open` / Windows: `startfile` / Linux: `xdg-open`）
- checkbox 互斥逻辑：通过 `data-group` 属性标识同一主图分组，监听 `change` 事件时取消同组内其他 checkbox 的选中状态
- 主图列使用 `rowspan` 合并同组候选行，避免重复展示
- ⚠️ Python 源码中所有 emoji 必须使用真实字符（如 `📋`），**禁止使用 UTF-16 代理对转义**（如 `\ud83d\udccb`），否则会触发 `surrogates not allowed` UTF-8 编码错误
