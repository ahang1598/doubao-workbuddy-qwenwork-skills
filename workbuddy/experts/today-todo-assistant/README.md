# Today Todo Assistant（腾讯公益今日待办专家团）

腾讯公益机构侧"今日待办"智能分派**专家团**。内置 1 位主理人 + 3 位成员专家，以团队协作模式帮机构工作人员统一查看并分派当日待办（留言运营 / 证件与备案号更新 / 票据处理），点击后调度对应成员专家处理。

## 内置成员专家（无需单独安装）

| 成员专家 | 职责 |
|-----|------|
| `comment-assistant`（腾讯公益留言运营专家） | 留言批量回复处理 |
| `alert-expert`（腾讯公益备案号证件更新专家） | 证件 / 备案号更新处理 |
| `invoice-expert`（腾讯公益捐赠票据处理专家） | 票据 OCR + 匹配 + 批量提交 |

## 依赖

仅依赖连接器 **`gongyi-open-mcp`**（腾讯公益开放 MCP），安装本包前请确保该连接器已连接。

## 功能

用户唤起后，主理人一次性拉取四类待办聚合数据，汇总成可点击菜单（只展示有待办的项），用户点击对应项后调度相应成员专家进入处理，处理完可继续下一项。

## 使用示例

- "帮我看看今天有什么要处理的"
- "处理今日待办"
- "有留言要回复吗？"

## 安装

放到 workbuddy 专家目录：

```
C:\Users\<user>\.workbuddy\plugins\marketplaces\<market>\plugins\today-todo-assistant\
```

## 打包分享

```bash
zip -r today-todo-assistant.zip today-todo-assistant/
```

## 头像

- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB
