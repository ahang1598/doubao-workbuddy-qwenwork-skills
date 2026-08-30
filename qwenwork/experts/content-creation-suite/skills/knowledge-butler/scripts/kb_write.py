#!/usr/bin/env python3
"""
kb_write.py · 知识管家 helper 脚本 · 通过 stdin 写文件到指定路径

═══════════════════════════════════════════════════════════════════
为什么要这个脚本（不能用 LLM 的 create_file/Write 工具）
═══════════════════════════════════════════════════════════════════

悟空 sandbox 的 deliver hook 有"双重策略"：
  - 路径 A（脚本写文件）：hook 不追踪 → 不创建独立 deliver entry
  - 路径 B（LLM Write 工具写文件）：hook 自动追踪 → 为每个文件建独立 entry

批量写编译产物时（如一次任务写 10+ 摘要/专题/洞察），如果走路径 B，悟空 UI
"项目文件"侧边栏顶层会出现 10+ 个孤立 .md 项 —— 用户体验严重混乱。

通过本脚本（Python os.write）写文件 → 走路径 A → hook 不追踪 → UI 干净。

═══════════════════════════════════════════════════════════════════
用法
═══════════════════════════════════════════════════════════════════

  .venv/bin/python scripts/kb_write.py <绝对路径> <<'KB_EOF'
  <markdown 内容>
  KB_EOF

注意 heredoc 用 quoted EOF（'KB_EOF' 加引号）——不展开变量，安全包含
任何特殊字符（反引号、$、引号、emoji 等）。

═══════════════════════════════════════════════════════════════════
完整示例
═══════════════════════════════════════════════════════════════════

  .venv/bin/python scripts/kb_write.py \\
      "$KB_ROOT/2-AI知识库/专题/Karpathy.md" <<'KB_EOF'
  ---
  title: Karpathy
  type: topic
  entity_kind: person
  ---

  ## 简介
  Andrej Karpathy 是 OpenAI 创始团队成员、前 Tesla AI 主管。

  ## Timeline
  - **2026-04-21** | 首次出现 [[摘要-04-21-LM-Wiki方法论]]

  ## 被提到
  - **2026-04-21** | [[摘要-04-21-LM-Wiki方法论]] — 提出 LM Wiki 概念
  KB_EOF

═══════════════════════════════════════════════════════════════════
适用范围
═══════════════════════════════════════════════════════════════════

✅ 必须用本脚本的场景（批量写场景，hook 路径 B 翻车点）：
  - Workflow 1 第二阶段：写素材摘要 / 专题页 / 洞察页
  - Workflow 5 Phase 1.5：持续编译生成的洞察草稿
  - Workflow 6：日报生成
  - 任何"一次任务写 ≥3 个文件"的场景

❌ 不需要本脚本的场景（用 LLM 的 create_file/modify_file 即可）：
  - 初始化时写说明文件（一次 ≤7 个，hook 追踪也只多 7 entry，可接受）
  - 操作记录追加（用 modify_file 增量更新，不创建新 entry）
  - 规则手册更新（同上）

═══════════════════════════════════════════════════════════════════
安全检查（脚本自带）
═══════════════════════════════════════════════════════════════════

1. 路径必须是 .md 文件（防误写其他类型）
2. 路径必须在 $HOME/Desktop/知识管家/ 内（防写到 workspace 或系统目录）
3. stdin 不能为空
4. 父目录自动创建（mkdir -p）
"""

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "❌ 用法: .venv/bin/python scripts/kb_write.py <绝对路径>\n"
            "   内容从 stdin 读取（heredoc / 管道）",
            file=sys.stderr,
        )
        return 1

    target_arg = sys.argv[1]
    target = Path(target_arg).expanduser().resolve()

    # 安全检查 1: 必须是 .md 文件
    if target.suffix.lower() != ".md":
        print(
            f"❌ 拒绝：仅支持 .md 文件（你给的是 '{target.suffix}'）\n"
            f"   path: {target}",
            file=sys.stderr,
        )
        return 2

    # 安全检查 2: 必须在 $HOME/Desktop/知识管家/ 内（防止写错位置）
    home = Path.home()
    kb_root_default = (home / "Desktop" / "知识管家").resolve()
    try:
        target.relative_to(kb_root_default)
    except ValueError:
        # 允许用户指定其他 KB_ROOT，但要警告（不致命）
        kb_root_env = Path(
            __import__("os").environ.get("KB_ROOT", str(kb_root_default))
        ).expanduser().resolve()
        try:
            target.relative_to(kb_root_env)
        except ValueError:
            print(
                f"❌ 拒绝：目标不在 KB_ROOT 内\n"
                f"   target:  {target}\n"
                f"   kb_root: {kb_root_env}",
                file=sys.stderr,
            )
            return 3

    # 读 stdin
    content = sys.stdin.read()
    if not content.strip():
        print("❌ 拒绝：stdin 内容为空", file=sys.stderr)
        return 4

    # 父目录自动创建
    target.parent.mkdir(parents=True, exist_ok=True)

    # 写文件（utf-8）
    target.write_text(content, encoding="utf-8")

    # 成功提示（含字数 + 路径，方便 LLM 自检）
    char_count = len(content)
    line_count = content.count("\n") + 1
    print(
        f"✓ 写入成功 [{char_count} 字符 · {line_count} 行]\n"
        f"  → {target}\n"
        f"  hook 不会追踪此文件（os.write 写入 = deliver 路径 A 不触发）"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
