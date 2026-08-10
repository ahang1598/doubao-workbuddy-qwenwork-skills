# 多素材组装契约

组装用于把两份或多份现有素材整理为一份新文稿。它不是随意改写：源素材保持只读，输出写入新的 Markdown 真源，重复内容可以删并，但各素材中被用户指定为必须保留的数据、观点、名称、时间线和引语必须可追踪。

## 一、开工前冻结

在写正文前确认：源素材文件清单、各素材的核心保留项、允许删除的重复内容、禁止新增的观点、目标结构、目标字数及允许浮动范围。不要把具体业务题目写进通用规则。

## 二、保护契约

开工前把当前组装的保护契约写入 `.doubao-book-writer/preservation-contract.json`，声明各源素材为只读、输出目标为可整体重写：

```json
{
  "schema": "doubao-preservation-contract-v1",
  "route": "assemble",
  "files": [
    { "path": "materials/source-a.txt", "mode": "read-only" },
    { "path": "materials/source-b.md", "mode": "read-only" },
    { "path": "manuscript.md", "mode": "whole-file" }
  ]
}
```

首次写入前先备份全部源素材。组装完成后确认源素材字节未变；成稿必须写在 `.doubao-book-writer/` 之外的正文真源。

## 三、组装质量

- 重复内容优先合并，不机械保留两份相同表述。
- 保留项在新稿中可以调整位置，但不得改变数据和原意。
- 用户禁止新增观点时，只能补充连接和结构说明，不能加入外部判断。
- 成稿仍遵守标题、列表、callout、来源和写作形态规则。
- 结束前执行实际字数核验，不使用模型估算。
