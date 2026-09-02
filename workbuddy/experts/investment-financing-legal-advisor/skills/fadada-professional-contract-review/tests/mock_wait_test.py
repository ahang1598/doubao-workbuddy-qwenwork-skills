#!/usr/bin/env python3
"""验证 get_review_result.py --wait：mock 服务前 2 次返回 PROCESSING，第 3 次 COMPLETED。

用法: python3 tests/mock_wait_test.py scripts/get_review_result.py
"""
import json, os, subprocess, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

SCRIPT = sys.argv[1]
state = {"count": 0, "always": False}


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        state["count"] += 1
        if state["always"] or state["count"] < 3:
            data = {"reviewStatus": "PROCESSING"}
        else:
            data = {"reviewStatus": "COMPLETED", "riskItems": [{"id": 1}], "summary": "mock 完整结果"}
        body = json.dumps({"code": "000000", "success": True, "data": data}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
env = dict(os.environ, RICHEEAI_TOKEN="fake",
           RICHEEAI_API_BASE=f"http://127.0.0.1:{srv.server_address[1]}")
fails = []


def run(label, args, expect):
    p = subprocess.run([sys.executable, SCRIPT] + args, capture_output=True, text=True, env=env, timeout=60)
    try:
        out = json.loads(p.stdout.strip())
    except Exception:
        fails.append(f"{label}: stdout 非 JSON: {p.stdout[:80]}")
        return None
    for k, v in expect.items():
        if out.get(k) != v:
            fails.append(f"{label}: {k} 期望 {v!r} 实际 {out.get(k)!r}")
    return out


state.update(count=0, always=False)
o = run("wait完成", ["rec-1", "--wait", "--interval", "1"],
        {"success": True, "reviewStatus": "COMPLETED", "recordId": "rec-1", "polls": 3})
if o and not (o.get("resultFile") and os.path.exists(o["resultFile"])):
    fails.append("wait完成: resultFile 未落盘")

state.update(count=0, always=True)
run("wait超时", ["rec-2", "--wait", "--interval", "1", "--max-wait", "5"],
    {"success": True, "reviewStatus": "PROCESSING", "timedOut": True})

state.update(count=0, always=True)
o = run("单发非终态", ["rec-3"], {"success": True, "reviewStatus": "PROCESSING"})
if o and len(o) > 2:
    fails.append(f"单发非终态: 输出应仅 2 键, 实际 {o}")

state.update(count=10, always=False)
run("单发终态", ["rec-4"], {"success": True, "reviewStatus": "COMPLETED"})

srv.shutdown()
if fails:
    print("WAIT-TEST FAIL: " + "; ".join(fails))
    sys.exit(1)
print("WAIT-TEST ALL PASSED")
