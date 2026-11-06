# 技能初始化（安装后必须执行一次）

技能安装后，必须初始化模板项目，后续一键成片才能正常工作。

## 检查是否已初始化

```bash
bash "$XIAOYI_VLOG_DIR/scripts/check-init.sh"
```

退出码 0 → 已初始化，跳过。
退出码 1/2 → 执行下方步骤重新初始化。

## 步骤1：拷贝预制模板

拷贝预制模板骨架：

```bash
SKEL="$XIAOYI_VLOG_DIR/assets/template-skeleton"
TARGET="$XIAOYI_VLOG_DIR/.runtime/template"

mkdir -p "$TARGET"
cp -r "$SKEL"/. "$TARGET"/
```

## 步骤2：配置 Chrome 路径

Remotion 需要无头浏览器渲染，必须在 `remotion.config.ts` 中指定 Chrome 路径。

**自动检测并写入：**

```bash
TEMPLATE="$XIAOYI_VLOG_DIR/.runtime/template"

# 优先级：环境变量 > 系统 PATH > Remotion 缓存
# 逐个尝试，验证可执行后才采用
find_chrome() {
  [ -n "$CHROME_PATH" ] && "$CHROME_PATH" --version &>/dev/null && return
  CHROME_PATH=""
  for cmd in chromium-browser google-chrome chromium /opt/google/chrome/google-chrome /opt/chromium/chromium /opt/chrome-linux/chrome; do
    p=$(which $cmd 2>/dev/null) && [ -n "$p" ] && "$p" --version &>/dev/null && { CHROME_PATH="$p"; return; }
  done
  CACHED="$HOME/.cache/remotion/chrome-headless-shell/chrome-headless-shell-linux64/chrome-headless-shell"
  [ -x "$CACHED" ] && "$CACHED" --version &>/dev/null && { CHROME_PATH="$CACHED"; return; }
}
find_chrome

if [ -z "$CHROME_PATH" ]; then
  echo '❌ 未找到 Chrome/Chromium，请手动设置 CHROME_PATH 环境变量后重试'
  echo '   下载方式：'
  echo '   1. 从 https://googlechromelabs.github.io/chrome-for-testing/ 下载 chrome-headless-shell'
  echo '   2. 放到 ~/.cache/remotion/chrome-headless-shell/ 下'
  echo '   3. 设置 CHROME_PATH 后重新执行'
  exit 1
fi

echo "✅ 检测到 Chrome: $CHROME_PATH"

# 重写 remotion.config.ts（含 Chrome 路径）
cat > $TEMPLATE/remotion.config.ts << CONF
import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setChromeMode("chrome-for-testing");
Config.setBrowserExecutable("$CHROME_PATH");
CONF
```

## 步骤3：确认依赖

Remotion/React 已由小艺 Work 根据 Skill 根目录的 `package-lock.json` 后台安装到 `$XIAOYI_VLOG_DIR/node_modules`。调用阶段禁止执行 `npm install`。若依赖未就绪，等待后台安装完成或在技能页重试。


## 步骤4：环境检查

初始化完成后，运行以下检查确认环境正常：

```bash
TEMPLATE="$XIAOYI_VLOG_DIR/.runtime/template"
cd "$TEMPLATE"

# 渲染单帧测试（验证 Chrome + 依赖 + 组件 + props 完整链路）
cat > /tmp/vlog-test.json << 'EOF'
{"title":"Test","subtitle":"Check","endText":"OK","scenes":[{"image":"test.jpg","animation":"zoom-in","transition":"fade"}],"sceneDurations":[120]}
EOF
"$XIAOYI_VLOG_DIR/node_modules/.bin/remotion" still src/index.ts MainComposition /tmp/vlog-preview.png \
  --frame=30 --scale=0.25 --props=/tmp/vlog-test.json && echo '✅ 环境正常' || echo '❌ 渲染失败'
```

渲染失败常见原因：Chrome 路径、图片路径、props 格式，查看 Remotion 错误日志排查。

## 步骤5：前置技能说明

每次任务会按 `SKILL.md` 第0步检查以下工具/技能：

- **图像理解**工具或技能：必需，缺少时通过 `find-skills` 安装，否则不能继续
- **seedream-image_gen**：可选，缺少时用户可选择纯文字封面/片尾
- **minimax-music-gen-win**：可选，缺少时用户可提供/复用音乐或选择无 BGM

技能缺失不属于生成失败，不得在能力检查前展示 BGM 生成的20点确认，也不得未经用户同意自动降级。

## 初始化完成后的目录结构

```
<skill_dir>/
├── node_modules/                       # 小艺 Work 后台安装，只安装一次
├── .runtime/template/                  # 可重建的运行模板
│   ├── package.json
│   ├── tsconfig.json
│   ├── .npmrc
│   ├── remotion.config.ts
│   ├── public/                         # 当前项目的 images/audio（每次渲染前复制）
│   │   ├── images/
│   │   └── audio/
│   └── src/
│       ├── index.ts                    # 入口
│       ├── Root.tsx                    # Composition 定义
│       └── MainComposition.tsx         # 主组件
└── <任务工作空间>/YYYYMMDD_HHMMSS/     # 每次一键成片的输出目录
    ├── images/                         # 输入图片
    ├── audio/                          # BGM 背景音乐
    ├── script.json                     # 编排表 + BGM 信息
    └── out/                            # 最终渲染输出
```
