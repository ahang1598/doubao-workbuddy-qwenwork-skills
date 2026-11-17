# paper-search · paper-search（WorkBuddy 专家包）

> **版本**：v2.0.0 ｜ **生成日期**：2026-09-13 ｜ **作者**：清风明月（809277254@qq.com）
> **平台**：WorkBuddy / CodeBuddy 开放平台 ｜ **专家类型**：agent

## 一、专家简介

学术论文检索技能（OpenAlex 250M+ 文献，免费无 API Key）。按关键词检索论文，或按 DOI / OpenAlex ID 查单篇详情（作者、被引、摘要、开放获取链接）；OpenAlex 429 限流时自动降级 Semantic Scholar。当用户需要查文献、找论文、学术检索、按 DOI 查文章、查被引次数、找开放获取 PDF、写研究/报告要科学依据时使用。Search for

## 二、能力概览

- 技能目录：`skills/paper-search/`（含 SKILL.md、references×0、scripts×0）
- 定位：paper-search
- 触发方式：直接描述你的需求，专家自动匹配工作流

## 三、目录结构

```
paper-search/
├── .codebuddy-plugin/
│   └── plugin.json          # 平台元数据（i18n 双语）
├── avatars/
│   └── expert.png           # 512×512 头像
├── agents/
│   └── paper-search.md     # 智能体定义（frontmatter 禁 tools）
├── skills/
│   └── paper-search/       # 完整技能包
│       ├── SKILL.md
│       ├── references/      # 0 份专家件
│       └── scripts/         # 0 个脚本
└── README.md
```

## 四、上架发布

1. 打开 WorkBuddy【专家中心 → 我的专家】
2. 上传本 zip
3. 检查头像/名称/描述/标签/推荐提示词展示效果
4. 确认无误后点击发布

如遇解析报错，可邮件 `openworkbuddy@tencent.com`。

## 五、版本历史

- **v2.0.0**（2026-09-13）：首次 WorkBuddy 专家包化
