#!/usr/bin/env bash
#
# 学校舆情监控技能 - 测试运行器
# 用法: bash tests/run_tests.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
PASS=0
FAIL=0
TOTAL=0

echo "===== 学校舆情监控技能 - 自动化测试 ====="
echo ""

# ---------- 辅助函数 ----------
pass_test() {
    PASS=$((PASS + 1))
    TOTAL=$((TOTAL + 1))
    echo "  [PASS] $1"
}

fail_test() {
    FAIL=$((FAIL + 1))
    TOTAL=$((TOTAL + 1))
    echo "  [FAIL] $1 - $2"
}

# ---------- 测试 1: manage_task.py create ----------
echo "--- 测试 1: 创建任务 ---"
TEST_DIR=$(mktemp -d)
TEST_TASKS="$TEST_DIR/test-sentiment-tasks-$$.json"

CREATE_OUTPUT=$(echo '{"school_name":"杭州云谷学校","aliases":["云谷学校","云谷"],"time_range":"7d","frequency":"daily","execute_time":"08:00"}' | python3 "$SKILL_DIR/scripts/manage_task.py" create "$TEST_TASKS" 2>&1)

if echo "$CREATE_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['task_id']" 2>/dev/null; then
    pass_test "创建任务返回有效 task_id"
else
    fail_test "创建任务" "输出不包含有效 task_id"
fi

if echo "$CREATE_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['config']['school_name']=='杭州云谷学校'" 2>/dev/null; then
    pass_test "任务配置 school_name 正确"
else
    fail_test "任务配置" "school_name 不正确"
fi

if echo "$CREATE_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='active'" 2>/dev/null; then
    pass_test "新任务状态为 active"
else
    fail_test "任务状态" "新任务状态不是 active"
fi

TASK_ID=$(echo "$CREATE_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])" 2>/dev/null)

# ---------- 测试 2: manage_task.py list ----------
echo ""
echo "--- 测试 2: 列出任务 ---"
LIST_OUTPUT=$(python3 "$SKILL_DIR/scripts/manage_task.py" list "$TEST_TASKS" 2>&1)

if echo "$LIST_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d)>=1" 2>/dev/null; then
    pass_test "列出任务返回非空列表"
else
    fail_test "列出任务" "返回空列表"
fi

# ---------- 测试 3: manage_task.py read ----------
echo ""
echo "--- 测试 3: 读取任务 ---"
READ_OUTPUT=$(python3 "$SKILL_DIR/scripts/manage_task.py" read "$TEST_TASKS" "$TASK_ID" 2>&1)

if echo "$READ_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['task_id']=='$TASK_ID'" 2>/dev/null; then
    pass_test "按 task_id 读取任务成功"
else
    fail_test "读取任务" "返回的 task_id 不匹配"
fi

# ---------- 测试 4: manage_task.py pause / resume ----------
echo ""
echo "--- 测试 4: 暂停/恢复任务 ---"
PAUSE_OUTPUT=$(python3 "$SKILL_DIR/scripts/manage_task.py" pause "$TEST_TASKS" "$TASK_ID" 2>&1)

if echo "$PAUSE_OUTPUT" | grep -q "已暂停"; then
    pass_test "暂停任务成功"
else
    fail_test "暂停任务" "输出不包含暂停确认"
fi

# 验证状态确实变为 paused
READ_PAUSED=$(python3 "$SKILL_DIR/scripts/manage_task.py" read "$TEST_TASKS" "$TASK_ID" 2>&1)
if echo "$READ_PAUSED" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='paused'" 2>/dev/null; then
    pass_test "暂停后状态为 paused"
else
    fail_test "暂停状态验证" "状态不是 paused"
fi

RESUME_OUTPUT=$(python3 "$SKILL_DIR/scripts/manage_task.py" resume "$TEST_TASKS" "$TASK_ID" 2>&1)

if echo "$RESUME_OUTPUT" | grep -q "已恢复"; then
    pass_test "恢复任务成功"
else
    fail_test "恢复任务" "输出不包含恢复确认"
fi

# ---------- 测试 5: manage_task.py update ----------
echo ""
echo "--- 测试 5: 更新任务 ---"
UPDATE_OUTPUT=$(echo '{"config":{"frequency":"hourly"}}' | python3 "$SKILL_DIR/scripts/manage_task.py" update "$TEST_TASKS" "$TASK_ID" 2>&1)

if echo "$UPDATE_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['config']['frequency']=='hourly'" 2>/dev/null; then
    pass_test "更新频率为 hourly 成功"
else
    fail_test "更新任务" "频率未更新为 hourly"
fi

# ---------- 测试 6: manage_task.py delete ----------
echo ""
echo "--- 测试 6: 删除任务 ---"
DELETE_OUTPUT=$(python3 "$SKILL_DIR/scripts/manage_task.py" delete "$TEST_TASKS" "$TASK_ID" 2>&1)

if echo "$DELETE_OUTPUT" | grep -q "已删除"; then
    pass_test "删除任务成功"
else
    fail_test "删除任务" "输出不包含删除确认"
fi

# 验证删除后列表为空
LIST_AFTER=$(python3 "$SKILL_DIR/scripts/manage_task.py" list "$TEST_TASKS" 2>&1)
if echo "$LIST_AFTER" | grep -q "暂无"; then
    pass_test "删除后任务列表为空"
else
    fail_test "删除验证" "删除后仍有任务"
fi

# ---------- 测试 7: generate_report.sh ----------
echo ""
echo "--- 测试 7: 生成 HTML 报告 ---"

# 创建测试分析数据
python3 << 'PYEOF'
import json
data = {
    "task_id": "test_001",
    "school_name": "杭州云谷学校",
    "search_time": "2026-04-10 08:00:00",
    "period": "2026-04-03 ~ 2026-04-10",
    "total_count": 5,
    "sentiment_distribution": {"positive": 2, "neutral": 1, "negative": 2},
    "items": [
        {
            "title": "云谷学校春季运动会精彩纷呈",
            "summary": "学校举办春季运动会，学生们积极参与各项体育活动",
            "source": "抖音",
            "url": "https://example.com/1",
            "publish_time": "2026-04-08",
            "sentiment": "positive",
            "sentiment_score": 85,
            "topic": "T08",
            "severity": "normal",
            "keywords": ["运动会", "体育", "活动"]
        },
        {
            "title": "家长反映食堂菜品质量下降",
            "summary": "有家长在社交媒体发帖称食堂饭菜质量不如以前",
            "source": "微博",
            "url": "https://example.com/2",
            "publish_time": "2026-04-07",
            "sentiment": "negative",
            "sentiment_score": 72,
            "topic": "T04",
            "severity": "important",
            "keywords": ["食堂", "质量", "家长"]
        }
    ],
    "top_keywords": [
        {"word": "运动会", "count": 8, "sentiment": "positive"},
        {"word": "食堂", "count": 5, "sentiment": "negative"},
        {"word": "招生", "count": 4, "sentiment": "neutral"}
    ],
    "alerts": [
        {
            "title": "家长反映食堂菜品质量下降",
            "summary": "有家长在社交媒体发帖称食堂饭菜质量不如以前",
            "sentiment_score": 72,
            "url": "https://example.com/2",
            "source": "微博",
            "severity": "important"
        }
    ],
    "platform_distribution": {
        "抖音": 3,
        "微博": 1,
        "知乎": 1
    }
}
with open(os.path.join(os.environ.get("TEST_DIR", os.path.expanduser("~/.qwenworkcn/workspace/sentiment-monitor")), "test-sentiment-analysis.json"), "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
PYEOF

export TEST_DIR
REPORT_OUTPUT=$(bash "$SKILL_DIR/scripts/generate_report.sh" "$TEST_DIR/test-sentiment-analysis.json" "$TEST_DIR" 2>&1)

# 从输出中提取生成的文件路径
REPORT_FILE=$(ls -t "$TEST_DIR"/sentiment_report_*.html 2>/dev/null | head -1)

if [ -n "$REPORT_FILE" ] && [ -f "$REPORT_FILE" ]; then
    pass_test "HTML 报告文件生成成功"
else
    fail_test "生成报告" "HTML 文件未生成"
fi

if [ -n "$REPORT_FILE" ] && [ -f "$REPORT_FILE" ]; then
    if grep -q "杭州云谷学校" "$REPORT_FILE"; then
        pass_test "报告包含学校名称"
    else
        fail_test "报告内容" "不包含学校名称"
    fi

    if grep -q "情感分布" "$REPORT_FILE"; then
        pass_test "报告包含情感分布"
    else
        fail_test "报告内容" "不包含情感分布"
    fi
fi

# ---------- 清理（移到回收站，不使用 rm） ----------
mv -n "$TEST_TASKS" ~/.Trash/ 2>/dev/null || true
mv -n "$TEST_DIR/test-sentiment-analysis.json" ~/.Trash/ 2>/dev/null || true
mv -n "$TEST_DIR" ~/.Trash/ 2>/dev/null || true

# ---------- 结果汇总 ----------
echo ""
echo "===== 测试结果 ====="
echo "  总计: $TOTAL"
echo "  通过: $PASS"
echo "  失败: $FAIL"
echo ""

if [ $FAIL -gt 0 ]; then
    echo "  结果: 有 $FAIL 个测试失败"
    exit 1
else
    echo "  结果: 全部通过!"
    exit 0
fi
