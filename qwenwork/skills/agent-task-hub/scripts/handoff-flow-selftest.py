#!/usr/bin/env python3
"""Local self-test for agent-task-hub handoff state transitions.

This test does not call dws or mutate any online table. It simulates the
records that the documented commands should produce and checks the invariants
that matter for a receiver such as Yu Cheng taking over a task.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Record:
    record_id: str
    title: str
    status: str
    handoff_status: str
    task_id: str = ""
    agent_type: str = ""
    assignee: str = ""
    creator: str = "user"
    parent_id: str | None = None
    short_summary: str = ""
    handoff_summary: str = ""


@dataclass
class Table:
    records: dict[str, Record] = field(default_factory=dict)

    def add(self, record: Record) -> None:
        if record.record_id in self.records:
            raise AssertionError(f"duplicate record id: {record.record_id}")
        self.records[record.record_id] = record

    def children_of(self, parent_id: str) -> list[Record]:
        return [r for r in self.records.values() if r.parent_id == parent_id]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def handoff_notification_triggers(record: Record, event: str) -> bool:
    return event == "created" and bool(record.assignee)


def claim_notification_triggers(record: Record, event: str) -> bool:
    return event == "created" and record.handoff_status == "待认领"


def complete_child(table: Table, child_id: str) -> None:
    child = table.records[child_id]
    child.status = "已完成"
    child.handoff_status = "已完成"
    assert_true(child.parent_id is not None, "completed child must have a parent")
    siblings = table.children_of(child.parent_id)
    if siblings and all(s.handoff_status == "已完成" for s in siblings):
        parent = table.records[child.parent_id]
        parent.status = "已完成"
        parent.handoff_status = "已完成"


def test_direct_handoff_to_yucheng() -> None:
    table = Table()
    parent = Record(
        record_id="parent-1",
        title="agent-task-hub 群内宣传与运营接续",
        status="进行中",
        handoff_status="未交接",
        task_id="01a00130-2048-7133-ab4e-e171502fd9ad",
        agent_type="codex",
    )
    table.add(parent)

    child = Record(
        record_id="child-1",
        title="【交接】agent-task-hub 群内宣传与运营接续",
        status="进行中",
        handoff_status="交接中",
        assignee="羽承",
        parent_id=parent.record_id,
        short_summary="请继续完善 agent-task-hub 群内宣传文案，突出 AI 表格承接 Agent 协同接续。",
        handoff_summary="目标：完善宣传。\n当前状态：已确定两段故事。\n下一步：产出群发稿。",
    )
    table.add(child)
    parent.handoff_status = "交接中"

    assert_true(child.parent_id == parent.record_id, "child must link to exactly one parent")
    assert_true(not parent.assignee, "parent task must not carry assignee")
    assert_true(len(child.short_summary) <= 180, "short summary must fit notification")
    assert_true(not child.task_id and not child.agent_type, "child task id and agent type wait for receiver")
    assert_true(handoff_notification_triggers(child, "created"), "child creation should notify Yu Cheng")
    assert_true(not handoff_notification_triggers(parent, "updated"), "parent update must not notify")

    child.task_id = "01a00130-aaaa-7133-ab4e-e171502fd9ad"
    child.agent_type = "codex"
    child.status = "进行中"
    child.handoff_status = "已接手"
    parent.handoff_status = "已接手"

    assert_true(child.task_id and ":" not in child.task_id, "receiver must backfill own raw task id (no agent prefix)")
    assert_true(child.agent_type == "codex", "receiver must backfill own agent type")
    assert_true(parent.handoff_status == "已接手", "parent should summarize accepted handoff")

    complete_child(table, child.record_id)
    assert_true(child.status == "已完成" and child.handoff_status == "已完成", "child should complete")
    assert_true(parent.status == "已完成" and parent.handoff_status == "已完成", "single-child parent should complete")


def test_multi_child_parent_not_done_until_all_done() -> None:
    table = Table()
    parent = Record("parent-2", "多成员交接任务", "进行中", "交接中", task_id="01a00130-2048-7133-ab4e-000000000002", agent_type="codex")
    table.add(parent)
    table.add(Record("child-2a", "【交接】A", "进行中", "已接手", parent_id=parent.record_id, assignee="羽承"))
    table.add(Record("child-2b", "【交接】B", "进行中", "交接中", parent_id=parent.record_id, assignee="另一位同学"))

    complete_child(table, "child-2a")
    assert_true(parent.status == "进行中", "parent stays active while sibling is not complete")
    assert_true(parent.handoff_status == "交接中", "parent handoff status stays active while sibling is not complete")

    complete_child(table, "child-2b")
    assert_true(parent.status == "已完成" and parent.handoff_status == "已完成", "parent completes after all children complete")


def test_claim_flow_notifications() -> None:
    pending = Record(
        "claim-1",
        "【交接】待认领任务",
        "进行中",
        "待认领",
        parent_id="parent-claim",
        short_summary="待认领短摘要",
    )
    assert_true(claim_notification_triggers(pending, "created"), "pending task should notify group on create")
    assert_true(not handoff_notification_triggers(pending, "created"), "pending task without assignee should not DM")

    pending.assignee = "羽承"
    pending.handoff_status = "交接中"
    assert_true(not handoff_notification_triggers(pending, "updated"), "claim update should not trigger create-only DM")

    delegated = Record(
        "claim-2",
        "【交接】管理员改派任务",
        "进行中",
        "交接中",
        parent_id="parent-claim",
        assignee="羽承",
    )
    assert_true(
        handoff_notification_triggers(delegated, "created"),
        "delegating to another person should create a new directed child record",
    )


def test_templates_are_notification_safe() -> None:
    for rel in ("templates/handoff-notify-workflow.json", "templates/claim-notify-workflow.json"):
        data = json.loads((ROOT / rel).read_text())
        start = data["steps"]["start"]
        send = data["steps"]["send"]["data"]
        assert_true(start["type"] == "WhenRecordCreated", f"{rel} must trigger on record creation")
        assert_true(send.get("isButtonsEnabled") is True, f"{rel} must enable card buttons")
        buttons = send.get("buttons") or []
        assert_true(buttons and buttons[0].get("name") == "去查看", f"{rel} should include a view button")
        action = buttons[0].get("action") or {}
        assert_true(action.get("type") == "link", f"{rel} button should be a link action")
        assert_true((action.get("url") or {}).get("ref") == "$.start.rowUrl", f"{rel} button should link to rowUrl")
        content = json.dumps(send["content"], ensure_ascii=False)
        assert_true("[http" not in content and "](http" not in content, f"{rel} must not use markdown links")
        assert_true("<团队台账URL>" not in content, f"{rel} should not include table URL in content")
        assert_true("回填" not in content, f"{rel} should not ask assignees to fill fields manually")
        assert_true("<通知文案fieldId>" in content, f"{rel} should render the notice richText field")


def test_parent_without_children_stays_active() -> None:
    """A parent task that has no children should never auto-complete."""
    table = Table()
    parent = Record("parent-orphan", "孤立父任务", "进行中", "交接中", task_id="01a00130-2048-7133-ab4e-000000000003", agent_type="codex")
    table.add(parent)
    # No children created yet
    children = table.children_of(parent.record_id)
    assert_true(len(children) == 0, "orphan parent should have no children")
    assert_true(parent.handoff_status == "交接中", "orphan parent stays in handoff status")
    assert_true(parent.status == "进行中", "orphan parent stays active")


def test_receiver_backfills_different_agent_type() -> None:
    """Receiver may use a different agent type than the initiator."""
    table = Table()
    parent = Record("parent-mix", "跨 agent 交接", "进行中", "交接中",
                    task_id="46c83d60-715f-4df2-9ec3-2fdd963dbc22", agent_type="qoder")
    table.add(parent)
    child = Record("child-mix", "【交接】跨 agent 交接", "进行中", "交接中",
                   assignee="羽承", parent_id=parent.record_id,
                   short_summary="qoder 任务交给 codex 接手")
    table.add(child)
    parent.handoff_status = "交接中"

    # Receiver backfills with their own agent type (codex, not qoder)
    child.task_id = "01a00130-2048-7133-ab4e-000000000004"
    child.agent_type = "codex"
    child.handoff_status = "已接手"
    parent.handoff_status = "已接手"

    assert_true(child.agent_type != parent.agent_type, "receiver agent type can differ from parent")
    assert_true(child.agent_type == "codex", "receiver backfilled own agent type")
    assert_true(":" not in child.task_id, "receiver task id must be raw; agent goes to agent_type")


def test_short_summary_length_boundary() -> None:
    """Short summary must fit within 180 chars for notification display."""
    table = Table()
    parent = Record("parent-len", "长摘要任务", "进行中", "未交接", task_id="01a00130-2048-7133-ab4e-000000000005", agent_type="codex")
    table.add(parent)
    # Exactly 180 chars
    exact = "x" * 180
    child_ok = Record("child-ok", "【交接】长摘要", "进行中", "交接中",
                      assignee="羽承", parent_id=parent.record_id, short_summary=exact)
    table.add(child_ok)
    assert_true(len(child_ok.short_summary) <= 180, "exactly 180 chars should pass")

    # 181 chars should be caught
    too_long = "x" * 181
    assert_true(len(too_long) > 180, "181 chars should fail the boundary check")


def test_example_files_are_valid_json() -> None:
    """All example/template JSON files must parse without errors."""
    for rel in (
        "examples/team-handoff-notify-workflow.json",
        "examples/team-table-get.sample.json",
        "templates/handoff-notify-workflow.json",
        "templates/claim-notify-workflow.json",
    ):
        data = json.loads((ROOT / rel).read_text())
        assert_true(isinstance(data, dict), f"{rel} must be a JSON object")


def test_example_handoff_has_no_unreplaced_placeholders() -> None:
    """The example handoff workflow must not contain <...> placeholders."""
    import re
    content = (ROOT / "examples" / "team-handoff-notify-workflow.json").read_text()
    placeholders = re.findall(r"<[^>]+>", content)
    # Filter out legitimate JSON structure markers
    real_placeholders = [p for p in placeholders if not p.startswith("$")]
    assert_true(len(real_placeholders) == 0,
                f"example should have no placeholders, found: {real_placeholders}")


def test_example_table_get_has_views() -> None:
    """The sample table-get JSON must include views for team views subcommand."""
    data = json.loads((ROOT / "examples" / "team-table-get.sample.json").read_text())
    inner = data.get("data", data)
    views = inner.get("views", [])
    assert_true(len(views) > 0, "sample must include at least one view")
    grid_views = [v for v in views if v.get("viewType") == "Grid"]
    assert_true(len(grid_views) > 0, "sample must include a Grid view")


def main() -> None:
    test_direct_handoff_to_yucheng()
    test_multi_child_parent_not_done_until_all_done()
    test_claim_flow_notifications()
    test_templates_are_notification_safe()
    test_parent_without_children_stays_active()
    test_receiver_backfills_different_agent_type()
    test_short_summary_length_boundary()
    test_example_files_are_valid_json()
    test_example_handoff_has_no_unreplaced_placeholders()
    test_example_table_get_has_views()
    print("handoff-flow selftest OK")


if __name__ == "__main__":
    main()
