# Marketing Material Generator

一个面向飞书多维表格的电商营销素材生成 Skill。它会读取商品信息与原始图片，依次生成白底精修图、产品特写、详情页、场景图和 Cinemagraph 视频，并将结果回写到对应记录。

## 能力

- 从飞书 Base 读取商品资料和附件
- 生成 1 张白底精修图
- 生成 3 张产品细节特写
- 生成 4 张商品详情页核心图
- 生成 2 张高写实场景图
- 经用户确认后生成 1 个 Cinemagraph 视频
- 每个环节完成后立即回写 Base

## 安装

将本仓库克隆或下载到支持 `SKILL.md` 的 Agent 用户技能目录：

```bash
git clone https://github.com/cuiabner1-ux/marketing-material-generator.git
```

运行前需要：

- 已安装并登录 `lark-cli`
- 对目标飞书多维表格拥有读取、下载附件和写入权限
- 当前 Agent 环境具备图片生成与图生视频能力

## 使用

1. 打开[营销素材生成模板](https://bytedance.larkoffice.com/base/L6gAbtH9raeD57s8QZtcHHnsnjP?table=tblvaKMdPLeH4HmG&view=vewCai3t42)，点击右上角的「创建副本」，不要直接编辑原模板。
2. 在副本中填写产品名称、产品图、产品尺寸和产品价值点。
3. 将填写完成的副本链接发给 Agent，并说明要处理的商品名称或记录。例如：

```text
请为这个副本里的第一条待处理商品生成全套营销素材：
https://example.feishu.cn/base/...
```

完整触发条件、字段约定和执行流程见 [SKILL.md](SKILL.md)，各环节的提示词模板见 [references/prompts.md](references/prompts.md)。

## 注意

- 视频生成前必须由用户确认时长、比例和效果。
- 表格字段名允许略有差异，但需能按语义对应。
- 模型名和工具能力取决于实际运行环境。

## License

[MIT](LICENSE)
