#!/usr/bin/env python3
"""
批量为使用 amazon-product-scout-agent 的专家 CLAUDE.md 注入二次评分模块。

用法:
  python3 patch_scoring_to_agent.py <CLAUDE.md 路径>
  python3 patch_scoring_to_agent.py /root/.linkfox/workspaces/agents/xxx/CLAUDE.md

会自动检测并注入:
  1. skill 引用行（二次评分: call skill amazon-asin-dynamic-scoring）
  2. --json-output 标志到 product_scout_agent.py 命令
  3. "评分" 触发词到意图识别
  4. 评分步骤（画像收集 + 执行 + 输出 + 深度调研推荐）
  5. "评分" 到持续交互循环
  6. 输出规范增加评分 Excel 说明
"""
import re
import sys
from pathlib import Path

# ── 评分模块标准文本 ──

SKILL_REF_LINE = "二次评分：call skill `amazon-asin-dynamic-scoring`（画像驱动的 ASIN 动态评分引擎）"

SCORING_STEP = r"""## Step {n} — 二次评分（动态评分引擎）

选品完成后，主动询问用户：「是否需要按您的偏好做二次量化评分？可自定义价格带、毛利率、评分数上限等门槛，系统会自动打分排序。回复「评分」开始，或回复「跳过」直接看结果。」

用户说"评分""打分"时，调用 skill `amazon-asin-dynamic-scoring`：

### {n}.1 期望收集策略（画像驱动）

采用「用户画像 → 自动映射期望 → 确认/微调」三步策略：

**Step A：画像收集（AskUserQuestion，2轮）**

第 1 轮：画像收集（5 个问题分 2 次 AskUserQuestion，选项带通俗解释）

AskUserQuestion 第 1 批（3 个问题）：

| 问题 | 选项 | 解释（显示在选项 description 中） |
|------|------|------|
| 卖家类型 | 工厂型 | 自己有工厂或深度合作工厂，能控制成本和改款，利润空间更大 |
| | 贸易型 | 采购成品售卖，没有自有工厂，需要快速起量回本 |
| | 个人卖家 | 个人或小团队运营，资金和资源有限，优先选竞争小的品 |
| 资金规模 | <5万 | 启动资金较少，适合低价轻小商品，试错成本低 |
| | 5-20万 | 中等预算，价格带选择灵活，可覆盖大多数品类 |
| | 20万+ | 资金充裕，可做高客单价产品，也能承受更多竞争 |
| 物流模式 | FBA | 发到亚马逊仓库由亚马逊配送，时效快但需囤货 |
| | FBM | 自己仓储自己发货，灵活但时效慢 |
| | 混合 | 部分 FBA 部分 FBM，兼顾时效与灵活性 |

AskUserQuestion 第 2 批（2 个问题）：

| 问题 | 选项 | 解释（显示在选项 description 中） |
|------|------|------|
| 经营偏好 | 走量薄利 | 靠销量取胜，单件利润低但量大，要求产品生命周期长、趋势稳定 |
| | 中等利润 | 利润和销量兼顾，不极端，适合大多数卖家 |
| | 高利润小众 | 单件利润高但量小，优先选竞争少、价格高的细分品 |
| 风险偏好 | 保守 | 宁可少选也不选错，筛选标准更严格，可能漏掉一些潜力品 |
| | 稳健 | 平衡风险与机会，使用标准阈值 |
| | 激进 | 愿意承担更多风险抓机会，放宽筛选标准，入选品更多但需自己再甄别 |

第 2 轮：权重确认（AskUserQuestion）

根据画像自动生成权重后，**用自然语言展示完整参数摘要并逐项解释**，格式如下：

```
根据您的画像，系统生成了以下评分参数：

【筛选门槛】
- 价格区间：$20-$50（基于您的资金规模）
- 最低毛利率：30%（基于您的经营偏好）
- 最高评分数：1500（评论越多竞争越大，超过此数否决）
- 最低销量增长率：10%（增长太慢说明趋势不强）
- 上架时间：近3个月（只看新品）
- 亚马逊自营：不接受

【评分权重】（总分100分，决定各维度对排名的影响力）
- 低竞争 30分：评分数越少、卖家越少，得分越高。权重越高=越优先选竞争小的品
- 上升生命周期 30分：销量增长率越高、越新上架，得分越高。权重越高=越优先选上升趋势中的品
- 利润健康 25分：价格匹配度越高、毛利率越好，得分越高。权重越高=越优先选赚钱的品
- 准入门槛低 15分：评论少、有新品标识、刚上架，得分越高。权重越高=越优先选容易进去的品

【风险调节】（您的风险偏好为"稳健"，阈值不做调节）
```

然后 AskUserQuestion 询问：
- 选项 1：「确认使用以上参数」→ 直接执行评分
- 选项 2：「微调筛选门槛」→ 用户指定要改的门槛参数（价格/毛利率/评分数/增长率）
- 选项 3：「微调评分权重」→ 用户指定要改的权重分配（四项权重，总和须=100）

**Step B：执行评分（--profile 模式）**

```bash
python3 <skill_path>/scripts/score_asins.py \
  --profile <profile.json> \
  --data <scout_roundN_products.json> \
  --output scoring_result.xlsx \
  --json-out scoring_result.json
```

profile.json 示例：
```json
{
  "seller_type": "贸易型",
  "budget": "5-20万",
  "logistics": "FBA",
  "business_preference": "中等利润",
  "risk_preference": "稳健"
}
```

脚本内部自动调用 `profile_to_expectations()` 生成 9 项期望参数，再经 `normalize_expectations()` 应用 risk_preference 动态调节否决阈值。

**备选：直接期望模式（--expectations）**

用户已有明确期望参数时跳过画像，直接传 expectations.json 执行。

### {n}.3 评分输出

- 评分结果摘要（通过/否决数、等级分布 S/A/B/C）
- Top 10 推荐商品表（含四维度得分、加权总分、推荐等级、否决原因）
- 评分 Excel 文件路径

### {n}.4 深度调研推荐

评分引擎仅基于卖家精灵选产品字段做量化筛选，无法覆盖品牌集中度、价格历史、流量结构、专利风险等深度维度。对 S/A 级推荐产品，主动提示用户可使用以下专家做进一步调研：

| 调研维度 | 推荐专家 | 适用场景 |
|---------|---------|---------|
| 类目级市场洞察 | 蓝海扫描专家（amazon-niche-radar-pro） | 评估类目容量、品牌集中度、季节性、新品友好度 |
| 竞品深度拆解 | 竞品全景透视专家（competitor-reverse-analysis） | Keepa历史曲线、价格弹性、评论异常、生命周期阶段、流量结构 |
| 流量关键词分析 | 卖家精灵流量词反查（linkfox-sellersprite-traffic-keyword） | ABA点击/转化占比、自然词/广告词结构、购买率 |
| 价格/BSR历史趋势 | Keepa商品时序数据（linkfox-keepa-product-series） | 价格走势、BSR趋势、评分变化、卖家数量、月销量 |

提示话术：「以上 S/A 级产品已通过量化评分，但评分引擎仅覆盖卖家精灵数据维度。如需进一步验证品牌竞争格局、价格历史趋势、流量结构或专利风险，可使用蓝海扫描专家做类目级分析，或用竞品全景透视专家对单个 ASIN 做深度拆解。」

"""


def patch_file(filepath: str) -> bool:
    """Patch a CLAUDE.md file to add scoring module. Returns True if changes made."""
    path = Path(filepath)
    if not path.exists():
        print(f"ERROR: File not found: {filepath}")
        return False

    content = path.read_text(encoding="utf-8")

    # Check if already has the full scoring step (not just the reference line)
    if "二次评分（动态评分引擎）" in content:
        print(f"SKIP: {filepath} already has scoring step")
        return False

    # Check if it uses amazon-product-scout-agent
    if "amazon-product-scout-agent" not in content:
        print(f"SKIP: {filepath} does not use amazon-product-scout-agent")
        return False

    original = content
    changes = []

    # 1. Add skill reference line after amazon-product-scout-agent line (skip if already exists)
    pattern_ref = r"(主脚本：call skill `amazon-product-scout-agent`[^\n]*)"
    if re.search(pattern_ref, content) and SKILL_REF_LINE not in content:
        content = re.sub(
            pattern_ref,
            r"\1\n" + SKILL_REF_LINE,
            content
        )
        changes.append("skill 引用行")

    # 2. Add --json-output to product_scout_agent.py command
    if "--json-output" not in content:
        # Match the last line of the scout command (ends with --sort-desc true or similar, before closing ```)
        content = re.sub(
            r"(python3 <skill_path>/scripts/product_scout_agent\.py[^`]*?--sort-desc\s+\S+)\s*\n```",
            r"\1 \\\n  --json-output\n```",
            content
        )
        changes.append("--json-output 标志")

    # 3. Add "评分" trigger to intent recognition
    # Find the last bullet in the intent recognition section
    trigger_line = '- 用户说"评分""打分""二次筛选""精排" → 进入二次评分流程'
    if trigger_line not in content:
        # Try to find the end of the intent list (before the next ## section)
        intent_section = re.search(
            r"(## Step 1[^#]*?)(\n##\s)",
            content,
            re.DOTALL
        )
        if intent_section:
            insert_pos = intent_section.end() - len("\n## ")
            content = content[:insert_pos] + trigger_line + "\n" + content[insert_pos:]
            changes.append("评分触发词")

    # 4. Insert scoring step before the "呈现" step
    # Find the "呈现" step
    present_match = re.search(r"## Step (\d+) — 呈现", content)
    if present_match:
        present_num = int(present_match.group(1))
        scoring_num = present_num
        new_present_num = present_num + 1

        # Get the scoring step text with correct number
        scoring_text = SCORING_STEP.replace("{n}", str(scoring_num))

        # Insert before the 呈现 step
        content = content[:present_match.start()] + scoring_text + "\n" + content[present_match.start():]

        # Renumber all subsequent steps (reverse order to avoid cascade)
        for old_num in range(19, present_num - 1, -1):
            new_num = old_num + 1
            content = content.replace(f"## Step {old_num} —", f"## Step {new_num} —")
            content = content.replace(f"→ Step {old_num}", f"→ Step {new_num}")

        changes.append(f"评分步骤 (Step {scoring_num})")

    # 5. Add "评分" to interaction loop
    if "评分" not in content.split("持续交互")[1] if "持续交互" in content else True:
        # Find the interaction section and add 评分 entry
        interact_match = re.search(
            r"(## Step \d+ — 持续交互\n)(.*?)(\n## |\Z)",
            content,
            re.DOTALL
        )
        if interact_match:
            interact_content = interact_match.group(2)
            if '"评分"' not in interact_content:
                # Add before the last bullet (usually 定时选品)
                scoring_interact = '- "评分" → 二次评分步骤\n'
                # Find "定时选品" line and insert before it
                content = re.sub(
                    r'(- "定时选品")',
                    scoring_interact + r'\1',
                    content
                )
                changes.append("持续交互评分入口")

    # 6. Add scoring Excel note to output spec
    if "二次评分结果同样输出 Excel" not in content:
        # Find the Excel-only output spec
        content = re.sub(
            r"(对话中只呈现 Top 10 预览[^\n]*)",
            r"\1\n- 二次评分结果同样输出 Excel（评分表 + 推荐清单），对话中呈现 Top 10 评分摘要",
            content
        )
        changes.append("输出规范评分说明")

    if content == original:
        print(f"NO CHANGE: {filepath} (patterns not matched, may need manual edit)")
        return False

    path.write_text(content, encoding="utf-8")
    print(f"PATCHED: {filepath}")
    print(f"  Changes: {', '.join(changes)}")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 patch_scoring_to_agent.py <CLAUDE.md path> [<path2> <path3> ...]")
        print("       python3 patch_scoring_to_agent.py --all   (auto-find all agents)")
        sys.exit(1)

    if sys.argv[1] == "--all":
        # Auto-find all CLAUDE.md files in agents directory
        agents_dir = Path("/root/.linkfox/workspaces/agents")
        targets = sorted(agents_dir.glob("*/CLAUDE.md"))
        # Also check workspace root
        root_claude = Path("/root/.linkfox/workspaces/CLAUDE.md")
        if root_claude.exists():
            targets.append(root_claude)
    else:
        targets = [Path(p) for p in sys.argv[1:]]

    patched = 0
    skipped = 0
    for t in targets:
        if patch_file(str(t)):
            patched += 1
        else:
            skipped += 1

    print(f"\nDone: {patched} patched, {skipped} skipped")


if __name__ == "__main__":
    main()
