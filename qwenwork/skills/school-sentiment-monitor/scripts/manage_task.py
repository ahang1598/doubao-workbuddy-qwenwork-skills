#!/usr/bin/env python3
"""
学校舆情监控 - 任务配置管理器
用法: python3 manage_task.py <action> <config_path> [task_id]

action:
  create  - 创建新任务（从 stdin 读取 JSON 配置）
  read    - 读取任务配置
  update  - 更新任务配置（从 stdin 读取更新字段）
  delete  - 删除指定任务
  list    - 列出所有任务
  pause   - 暂停指定任务
  resume  - 恢复指定任务
"""

import json
import sys
import os
import uuid
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
# 默认将任务配置写入 QoderWork 工作区下的固定目录（跨会话持久化，供定时任务使用）
TASKS_FILE_DEFAULT = os.path.join(
    os.path.expanduser("~/.qwenworkcn/workspace/sentiment-monitor"),
    "tasks.json",
)


def ensure_dir(path):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def load_tasks(path):
    if not os.path.exists(path):
        return {"tasks": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tasks(data, path):
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def create_task(config_path):
    """从 stdin 读取任务配置 JSON 并创建任务"""
    raw = sys.stdin.read().strip()
    if not raw:
        print("ERROR: 未提供任务配置数据（请通过 stdin 传入 JSON）", file=sys.stderr)
        sys.exit(1)

    config = json.loads(raw)
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    now = datetime.now(CST).isoformat()

    task = {
        "task_id": task_id,
        "status": "active",
        "created_at": now,
        "updated_at": now,
        "config": {
            "school_name": config.get("school_name", ""),
            "aliases": config.get("aliases", []),
            "time_range": config.get("time_range", "7d"),
            "frequency": config.get("frequency", "daily"),
            "execute_time": config.get("execute_time", "08:00"),
            "timezone": config.get("timezone", "Asia/Shanghai"),
        },
        "alert_rules": {
            "negative_threshold": config.get("negative_threshold", 80),
            "interaction_threshold": config.get("interaction_threshold", 100),
            "sensitive_keywords": config.get("sensitive_keywords", []),
            "keyword_threshold_reduction": config.get("keyword_threshold_reduction", 30),
        },
        "notify": {
            "channels": config.get("channels", ["current_chat"]),
            "mention_users": config.get("mention_users", []),
        },
        "last_executed_at": None,
        "execution_count": 0,
    }

    data = load_tasks(config_path)
    data["tasks"].append(task)
    save_tasks(data, config_path)

    print(json.dumps(task, ensure_ascii=False, indent=2))


def read_task(config_path, task_id=None):
    """读取任务配置。如果指定 task_id 则读取单个任务，否则读取最新任务"""
    data = load_tasks(config_path)
    tasks = data.get("tasks", [])

    if not tasks:
        print("INFO: 暂无监控任务")
        return

    if task_id:
        for t in tasks:
            if t["task_id"] == task_id:
                print(json.dumps(t, ensure_ascii=False, indent=2))
                return
        print(f"ERROR: 未找到任务 {task_id}", file=sys.stderr)
        sys.exit(1)
    else:
        # 返回最新的 active 任务
        active = [t for t in tasks if t["status"] == "active"]
        if active:
            print(json.dumps(active[-1], ensure_ascii=False, indent=2))
        else:
            print(json.dumps(tasks[-1], ensure_ascii=False, indent=2))


def update_task(config_path, task_id):
    """从 stdin 读取更新字段 JSON 并更新任务"""
    if not task_id:
        print("ERROR: update 需要指定 task_id", file=sys.stderr)
        sys.exit(1)

    raw = sys.stdin.read().strip()
    updates = json.loads(raw) if raw else {}

    data = load_tasks(config_path)
    found = False
    for t in data["tasks"]:
        if t["task_id"] == task_id:
            found = True
            # 更新 config 子字段
            if "config" in updates:
                t["config"].update(updates["config"])
            if "alert_rules" in updates:
                t["alert_rules"].update(updates["alert_rules"])
            if "notify" in updates:
                t["notify"].update(updates["notify"])
            if "status" in updates:
                t["status"] = updates["status"]
            if "last_executed_at" in updates:
                t["last_executed_at"] = updates["last_executed_at"]
            if "execution_count" in updates:
                t["execution_count"] = updates["execution_count"]
            t["updated_at"] = datetime.now(CST).isoformat()
            save_tasks(data, config_path)
            print(json.dumps(t, ensure_ascii=False, indent=2))
            break

    if not found:
        print(f"ERROR: 未找到任务 {task_id}", file=sys.stderr)
        sys.exit(1)


def delete_task(config_path, task_id):
    """删除指定任务"""
    if not task_id:
        print("ERROR: delete 需要指定 task_id", file=sys.stderr)
        sys.exit(1)

    data = load_tasks(config_path)
    original_len = len(data["tasks"])
    data["tasks"] = [t for t in data["tasks"] if t["task_id"] != task_id]

    if len(data["tasks"]) == original_len:
        print(f"ERROR: 未找到任务 {task_id}", file=sys.stderr)
        sys.exit(1)

    save_tasks(data, config_path)
    print(f"OK: 任务 {task_id} 已删除")


def list_tasks(config_path):
    """列出所有任务"""
    data = load_tasks(config_path)
    tasks = data.get("tasks", [])

    if not tasks:
        print("INFO: 暂无监控任务")
        return

    result = []
    for t in tasks:
        result.append({
            "task_id": t["task_id"],
            "school_name": t["config"]["school_name"],
            "status": t["status"],
            "frequency": t["config"]["frequency"],
            "last_executed_at": t.get("last_executed_at"),
            "execution_count": t.get("execution_count", 0),
        })

    print(json.dumps(result, ensure_ascii=False, indent=2))


def pause_task(config_path, task_id):
    """暂停任务"""
    if not task_id:
        print("ERROR: pause 需要指定 task_id", file=sys.stderr)
        sys.exit(1)

    data = load_tasks(config_path)
    for t in data["tasks"]:
        if t["task_id"] == task_id:
            if t["status"] == "paused":
                print(f"INFO: 任务 {task_id} 已处于暂停状态")
                return
            t["status"] = "paused"
            t["updated_at"] = datetime.now(CST).isoformat()
            save_tasks(data, config_path)
            print(f"OK: 任务 {task_id} 已暂停")
            return

    print(f"ERROR: 未找到任务 {task_id}", file=sys.stderr)
    sys.exit(1)


def resume_task(config_path, task_id):
    """恢复任务"""
    if not task_id:
        print("ERROR: resume 需要指定 task_id", file=sys.stderr)
        sys.exit(1)

    data = load_tasks(config_path)
    for t in data["tasks"]:
        if t["task_id"] == task_id:
            if t["status"] == "active":
                print(f"INFO: 任务 {task_id} 已处于活跃状态")
                return
            t["status"] = "active"
            t["updated_at"] = datetime.now(CST).isoformat()
            save_tasks(data, config_path)
            print(f"OK: 任务 {task_id} 已恢复")
            return

    print(f"ERROR: 未找到任务 {task_id}", file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else TASKS_FILE_DEFAULT
    task_id = sys.argv[3] if len(sys.argv) > 3 else None

    actions = {
        "create": lambda: create_task(config_path),
        "read": lambda: read_task(config_path, task_id),
        "update": lambda: update_task(config_path, task_id),
        "delete": lambda: delete_task(config_path, task_id),
        "list": lambda: list_tasks(config_path),
        "pause": lambda: pause_task(config_path, task_id),
        "resume": lambda: resume_task(config_path, task_id),
    }

    if action not in actions:
        print(f"ERROR: 未知操作 '{action}'，支持: {', '.join(actions.keys())}", file=sys.stderr)
        sys.exit(1)

    actions[action]()


if __name__ == "__main__":
    main()
