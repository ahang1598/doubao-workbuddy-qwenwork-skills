"""Best-effort QC workflow observations. Business commands are never retried here."""
import argparse
import base64
from contextlib import closing, contextmanager
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
try:
    CONTRACT = json.loads((ROOT / "telemetry/contract.json").read_text(encoding="utf-8"))
except (OSError, ValueError):
    CONTRACT = {"entry_types": [], "steps": {}, "counts": []}
ROOT_STEPS = {"preflight", "search", "probe", "targets"}
MILESTONES = {"record": "recorded", "transcript": "transcripts", "mp4_delivery": "mp4_delivered",
              "minutes_delivery": "minutes_delivered", "review_choice": "continued", "review": "reviewed",
              "report_create": "generated", "report_delivery": "delivered"}


def disabled():
    return os.getenv("BYTEDLIVE_TELEMETRY_DISABLED", "").strip().lower() in ("1", "true")


def valid_id(value):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{32}", value) is not None


def operator_id():
    def numeric(value):
        if isinstance(value, str) and re.fullmatch("[0-9]{1,64}", value.strip()):
            return value.strip()

    explicit = numeric(os.getenv("BYTEDLIVE_DOUBAO_USER_ID"))
    if explicit:
        return explicit
    token = os.getenv("DOUBAO_OFFICE_BYTEDANCE_USER_ACCESS_TOKEN", "")
    if len(token) <= 65536 and token.count(".") == 2:
        try:
            part = token.split(".")[1]
            claims = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
            if isinstance(claims, dict) and claims.get("typ") == "access_token":
                return numeric(claims.get("uid"))
        except (ValueError, UnicodeError, RecursionError):
            pass


def database():
    root = Path(os.environ.get("DOUYIN_QC_STATE_DIR") or Path.home() / ".douyin-live-qc")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    db = sqlite3.connect(root / "telemetry.db", timeout=1)
    db.execute("CREATE TABLE IF NOT EXISTS flows (id TEXT PRIMARY KEY, state TEXT NOT NULL)")
    db.execute("""CREATE TABLE IF NOT EXISTS receipts (
        flow TEXT, target TEXT, step TEXT, attempt TEXT, outcome TEXT,
        PRIMARY KEY(flow, target, step, attempt, outcome))""")
    return db


def transmit(events):
    if not events or disabled():
        return
    # Do not give SDK scripts business credentials, host identities, or caller-supplied Node options.
    env = {k: os.environ[k] for k in ("PATH", "SystemRoot", "WINDIR", "HTTPS_PROXY", "NO_PROXY",
                                    "DOUYIN_LIVE_INSPECT_CONFIG_DIR", "HOME", "USERPROFILE",
                                    "LOCALAPPDATA", "XDG_CONFIG_HOME")
           if k in os.environ}
    try:
        subprocess.run(["node", str(ROOT / "telemetry/send.cjs")], input=json.dumps(events).encode(),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2, env=env)
    except (OSError, subprocess.SubprocessError):
        pass


def target_stage(facts):
    for step in MILESTONES:
        outcome = facts.get(step)
        if outcome not in ("success", "continued"):
            if step == "record" and facts.get("extract") == "failure":
                return "extract", "failure"
            if step == "review" and facts.get("scan") == "failure":
                return "scan", "failure"
            return step, outcome or ("waiting" if step == "review_choice" else "pending")
    return "complete", "success"


def snapshot(flow, state):
    counts = dict.fromkeys(CONTRACT["counts"], 0)
    tasks = state["tasks"]
    counts["targets"] = len(tasks)
    stages = []
    for facts in tasks.values():
        for step, key in MILESTONES.items():
            if step in ("report_create", "report_delivery") and facts.get("review_choice") != "continued":
                continue
            counts[key] += facts.get(step) in ("success", "continued")
        counts["materials"] += all(facts.get(s) == "success" for s in
                                   ("mp4_delivery", "minutes_delivery"))
        stages.append(target_stage(facts))
    # Surface an explicit blocker first, otherwise the least advanced unfinished target.
    stage, result = state["root"]
    if stages:
        order = list(CONTRACT["steps"]) + ["complete"]
        stage, result = min(stages, key=lambda s: (s[1] != "failure", order.index(s[0])))
    facts = dict(flow_id=flow, flow_started_at=state["started"], flow_revision=state["revision"],
                 entry_type=state["entry"], current_stage=stage, current_result=result, **counts)
    if state.get("uid"):
        facts["doubao_user_id"] = state["uid"]
    return facts


def begin(flow, entry):
    if disabled() or not valid_id(flow) or entry not in CONTRACT["entry_types"]:
        return
    state = dict(started=int(time.time()), revision=1, entry=entry, uid=operator_id(),
                 root=["entry", "started"], tasks={})
    with closing(database()) as db, db:
        inserted = db.execute("INSERT OR IGNORE INTO flows VALUES (?,?)", (flow, json.dumps(state))).rowcount
    if inserted:
        transmit([dict(command="qc.workflow.snapshot", facts=snapshot(flow, state))])


def task_ids(flow, count):
    return [uuid.uuid5(uuid.UUID(flow), str(i)).hex for i in range(1, count + 1)]


def mark(flow, step, outcome, *, task=None, attempt=None, reason=None, elapsed_ms=None,
         requested_s=None, actual_ms=None, targets=None):
    if disabled() or not valid_id(flow) or outcome not in CONTRACT["steps"].get(step, ()):
        return
    if (step in ROOT_STEPS) != (task is None) or (task is not None and not valid_id(task)):
        return
    if reason is not None and reason not in CONTRACT["reasons"]:
        return
    if attempt is None:
        attempt = uuid.uuid4().hex
    if not valid_id(attempt):
        return
    confirming = step == "targets" and outcome in ("confirmed", "preset")
    if confirming and (type(targets) is not int or not 1 <= targets <= 10000):
        return
    numbers = dict(elapsed_ms=elapsed_ms, requested_s=requested_s, actual_ms=actual_ms)
    if any(type(v) is not int or not 0 <= v < 2**53 for v in numbers.values() if v is not None):
        return
    events = []
    with closing(database()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT state FROM flows WHERE id=?", (flow,)).fetchone()
        if not row:
            return
        state = json.loads(row[0])
        if task and task not in state["tasks"]:
            return
        before = snapshot(flow, state)
        if confirming:
            if state["tasks"] and targets != len(state["tasks"]):
                return
            if not state["tasks"]:
                state["tasks"] = {tid: {} for tid in task_ids(flow, targets)}
        inserted = db.execute("INSERT OR IGNORE INTO receipts VALUES (?,?,?,?,?)",
                              (flow, task or "", step, attempt, outcome)).rowcount
        if not inserted:
            return
        if task:
            facts = state["tasks"][task]
            if facts.get(step) not in ("success", "continued"):
                facts[step] = outcome
        else:
            state["root"] = [step, outcome]
        after = snapshot(flow, state)
        # The two individual delivery receipts contribute to one materials milestone.
        milestone = any(after[k] != before[k] for k in
                        ("targets", "recorded", "transcripts", "materials", "continued", "reviewed", "generated", "delivered"))
        diagnostic = outcome in ("failure", "partial", "empty", "unknown")
        decision = outcome in ("deferred", "ended") and after != before
        if milestone or diagnostic or decision:
            state["revision"] += 1
            after["flow_revision"] = state["revision"]
            if diagnostic:
                after.update(step=step, outcome=outcome, reason=reason or "unknown", attempt_id=attempt)
                if task:
                    after["task_id"] = task
            events.append(dict(command="qc.workflow.snapshot", facts=after))
        db.execute("UPDATE flows SET state=? WHERE id=?", (json.dumps(state), flow))
    if events:
        transmit(events)


def safely(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except Exception:
        # Telemetry failure must not alter a business result, including its original exception.
        return None


@contextmanager
def observe(step, failure_reason):
    flow = os.getenv("DOUYIN_QC_FLOW_ID")
    task = None if step in ROOT_STEPS else os.getenv("DOUYIN_QC_TASK_ID")
    active = not disabled() and valid_id(flow) and (step in ROOT_STEPS or valid_id(task))
    result = {"outcome": "success"}
    start = time.monotonic()
    try:
        yield result
    except (KeyboardInterrupt, GeneratorExit):
        active = False
        raise
    except (Exception, SystemExit):
        result.update(outcome="failure", reason=result.get("reason", failure_reason))
        raise
    finally:
        if active:
            safely(mark, flow, step, task=task, elapsed_ms=int((time.monotonic() - start) * 1000), **result)


def duration_ms(path):
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "default=noprint_wrappers=1:nokey=1", path],
                                capture_output=True, text=True, timeout=3, check=True)
        seconds = float(result.stdout.strip())
        if math.isfinite(seconds) and 0 < seconds < 2**53 / 1000:
            return max(1, round(seconds * 1000))
    except (OSError, ValueError, subprocess.SubprocessError):
        pass


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    entry = commands.add_parser("begin")
    entry.add_argument("--entry", choices=CONTRACT["entry_types"], required=True)
    entry.add_argument("--flow")
    receipt = commands.add_parser("mark")
    receipt.add_argument("step", choices=CONTRACT["steps"])
    receipt.add_argument("outcome")
    receipt.add_argument("--flow", default=os.getenv("DOUYIN_QC_FLOW_ID"))
    receipt.add_argument("--task")
    receipt.add_argument("--attempt", required=True)
    receipt.add_argument("--reason", choices=CONTRACT["reasons"])
    receipt.add_argument("--targets", type=int)
    receipt.add_argument("--elapsed-ms", type=int)
    args = parser.parse_args()
    if args.command == "begin":
        flow = args.flow or uuid.uuid4().hex
        safely(begin, flow, args.entry)
        print(flow)
    else:
        values = vars(args).copy()
        del values["command"]
        safely(mark, **values)
        if (args.step == "targets" and args.outcome in ("confirmed", "preset") and
                valid_id(args.flow) and args.targets and 1 <= args.targets <= 10000):
            print(json.dumps(task_ids(args.flow, args.targets)))


if __name__ == "__main__":
    main()
