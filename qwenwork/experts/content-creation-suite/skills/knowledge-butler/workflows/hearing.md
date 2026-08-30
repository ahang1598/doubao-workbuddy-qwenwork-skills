# 工作流 5：钉钉听记整理

> 本文件按需加载——仅在钉钉听记场景才 Read。

**触发词**：见 SKILL.md frontmatter 描述。

**前置**：确认 `.venv/` 已初始化。

## Phase -1：环境自检

```bash
# 解析 KB_ROOT + 定位 SKILL_DIR + 确认 venv + 冒烟测试
if [ -z "${KB_ROOT:-}" ]; then
    KB_ROOT=$(grep -E "^kb_root:" "$PWD/MEMORY.md" 2>/dev/null | head -1 | sed -E 's/^kb_root:[[:space:]]*//; s/[[:space:]]+$//')
    KB_ROOT="${KB_ROOT/#\~/$HOME}"
fi
[ -z "$KB_ROOT" ] && KB_ROOT="$HOME/Desktop/知识管家"
export KB_ROOT

SKILL_DIR=$(find ~/.real/users/*/.skills -name SKILL.md -exec grep -l '^name: knowledge-butler' {} \; 2>/dev/null | head -1 | xargs dirname)

if [ ! -x "$SKILL_DIR/.venv/bin/python" ]; then
    (cd "$SKILL_DIR" && bash setup.sh)
fi

cd "$SKILL_DIR" && .venv/bin/python scripts/wukong_minutes_to_md.py --help 2>&1 | head -3

# 读规则手册
if [ -f "$KB_ROOT/规则手册.md" ]; then
    echo "📖 已加载规则手册"
fi
```

通过后 AI 必须实际 Read 规则手册，把内容作为本次任务最高优先级偏好。

## Phase 0：幂等检查

读 `操作记录.md` 最后一次 workflow 5 完成记录——今日已完成则 skip。

## Phase 0b：预检确认页

调用 `preflight-day` 获取清单，按模板输出确认页（含时间范围、总条数、分类分布、完整清单含链接）。

用户确认后进入**一路到底模式**——从 Phase 1 到结束不中断。

## Phase 1：批量拉取

```bash
.venv/bin/python scripts/kb_pipeline.py preflight-day \
    --date YYYY-MM-DD --category "类别" --scope mine
```

## Phase 2：读全文 + 编译落盘

1. 用 `read-source --uuid X` 读每条原文（强制全文）
2. 在 thinking 里草拟所有摘要 + 涉及实体段
3. 一次 `compile-day` 落盘

## Phase 6：完成回执

**前置：机械验证**

```bash
OUT="$KB_ROOT/1-素材/录音/"
TODAY=$(date +%Y-%m-%d)
ACTUAL=$(grep -l "fetched: .*$TODAY" "$OUT"/*.md 2>/dev/null | wc -l | tr -d ' ')
WATERMARK=$(grep -l "generator: wukong_minutes_to_md.py" "$OUT"/*.md 2>/dev/null | wc -l | tr -d ' ')
echo "今日新增 $ACTUAL 条 · 水印 $WATERMARK 个"
```

**用户面回执**（简洁）：

```
✅ 钉钉听记整理完成
  • 新增 N 篇原文 + N 篇摘要（会议 X / AI 听记 Y / AI 硬件 Z）
  • 新建专题：[[张总]]、[[产品周会]] ...
  📂 打开 Obsidian 查看完整知识库：~/Desktop/知识管家/
```

**抽样校对**：≤5 条全列，6-15 条抽 2 条，>15 条抽 3 条（首/中/末各 1）。

## Phase 7：水印验证

```bash
cd "$KB_ROOT/1-素材/录音/" && grep -l "generator: wukong_minutes_to_md.py" *.md | wc -l
```

水印数 < 整理数 → 告警停止。

## 单条分支

用户直接给听记 URL/UUID 时：解析 UUID → 预检 title → 确认 → fetch → 编译。

## Python 脚本调用规则（硬禁令）

1. **禁止绕过脚本直接用 `dws minutes` CLI**——涉及听记的操作只能通过 `wukong_minutes_to_md.py`
2. **禁止用 `get summary` 代替 `get transcription`**——管家要原文不要 AI 摘要
3. **调用前确认 `.venv/` 已初始化**
4. **脚本失败时不假装成功**
5. **`batch` 必须带 `--session-id`**——由 preflight 产出
6. **禁止无执行的"完成回执"**——没有工具调用就不许说"完成"
7. **知识管家内容只写 `$KB_ROOT/`**——不写悟空 workspace

## 日期参数速查

| 用户说 | 参数 |
|---|---|
| "最近 N 天" | `--days N` |
| "昨天" / "某一天" | `--since YYYY-MM-DDT00:00:00 --until YYYY-MM-DDT23:59:59` |
| "某个范围" | `--since <起>T00:00:00 --until <止>T23:59:59` |

`--days` 和 `--since/--until` 互斥。日期必须 ISO-8601 完整格式。
