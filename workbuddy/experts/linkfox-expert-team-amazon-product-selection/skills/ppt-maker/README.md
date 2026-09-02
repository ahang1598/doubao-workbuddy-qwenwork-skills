# ppt-maker

一个 opencode / Claude Code 通用 Skill：把任意文字内容生成为专业的单文件 HTML 演示稿（PPT），
支持 7 套主题 × 5 种风格，双击即可在浏览器里当幻灯片播放，无需 PowerPoint/Keynote。

## 安装

选择下面任意一种方式，把 `ppt-maker/` 这个文件夹整体放进对应目录即可，**无需改任何配置**，
下次打开 opencode 或 Claude Code 就会自动识别这个 skill。

### opencode

```bash
# 全局安装（对所有项目生效）
cp -r ppt-maker ~/.config/opencode/skill/
# 或者放到下面这个目录也会被自动扫描到
cp -r ppt-maker ~/.agents/skills/

# 只想在某个项目里用，放到项目目录下即可
cp -r ppt-maker /path/to/your-project/.opencode/skill/
```

### Claude Code

```bash
cp -r ppt-maker ~/.claude/skills/
```

安装完成后重启 opencode / Claude Code。之后只要在对话里说：
"帮我做个 PPT"、"生成一份演示稿"、"make a PPT" 之类的话，就会自动触发这个 skill。

## 目录结构

```
ppt-maker/
├── SKILL.md                  # skill 定义（触发条件 + 执行流程），必读
├── references/
│   └── generation-guide.md   # 生成规则细节（配色变量、页面类型等）
├── themes/                   # 7 套主题 CSS（black-fire / ocean-blue / royal-purple ...）
├── templates/                # 5 种风格模板（entrepreneur / corporate / creative ...）
├── assets/                   # 参考用的完整示例 HTML
└── output/                   # 生成的 PPT 默认保存位置（初始为空）
```

## 使用效果

- 单个 HTML 文件，双击浏览器打开即用，不依赖任何外部文件
- 1920×1080 满屏优化，同时兼容移动端响应式
- 内置右侧导航圆点、动态光斑背景、卡片 hover 动效
- 默认风格 entrepreneur + 主题 black-fire（黑底白字橙红强调），可用自然语言切换
  （"用亮色主题" / "用紫色" / "正式风格" / "简约风" / "用翻页模式" 等）

## License

MIT
