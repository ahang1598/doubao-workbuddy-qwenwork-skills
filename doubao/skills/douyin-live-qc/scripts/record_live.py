#!/usr/bin/env python3
"""Extract Douyin live FLV stream URL via Chrome DevTools Protocol and record it.

Handles the pitfalls learned in practice:
  - auto-discovers a usable browser tab (tab ids change between sessions)
  - unescapes \\u0026 back to & in extracted URLs
  - prefers quality _or4 (FULL_HD1) > _hd > _sd > _ld
  - stream ids rotate every session, so URLs must always be fetched live
  - signed URLs expire (~1h), so record immediately after extraction

Usage:
    # extract only
    python3 record_live.py --room 641012837749 --extract-only

    # extract + record 300s
    python3 record_live.py --room 641012837749 --duration 300 --output out.mp4

Requires: websocket-client, requests, ffmpeg, a Chrome running with
--remote-debugging-port=9222 and a logged-in Douyin session.
"""
import argparse
from qc_telemetry import disabled, duration_ms, observe, valid_id
import json
import os
import re
import subprocess
import sys
import time

import requests
import websocket
from live_source import LiveSourceError, observe_room, room_input

CDP_BASE = "http://127.0.0.1:9222"
QUALITY_ORDER = ["_or4", "_hd", "_sd", "_ld"]

EXTRACT_JS = r"""
(function() {
    var urls = [];
    try {
        var entries = performance.getEntriesByType('resource');
        for (var i = 0; i < entries.length; i++) {
            if (entries[i].name && entries[i].name.indexOf('.flv') !== -1) {
                urls.push(entries[i].name);
            }
        }
    } catch (e) {}
    try {
        var scripts = document.querySelectorAll('script');
        for (var j = 0; j < scripts.length; j++) {
            var text = scripts[j].textContent;
            if (text && text.indexOf('.flv') !== -1) {
                var m = text.match(/https?:\/\/[^"']+\.flv[^"']*/g);
                if (m) urls = urls.concat(m);
            }
        }
    } catch (e) {}
    return JSON.stringify(urls);
})()
"""


def pick_tab():
    """Return webSocketDebuggerUrl of a usable page tab, creating one if needed."""
    try:
        tabs = requests.get(f"{CDP_BASE}/json/list", timeout=10).json()
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"[fatal] cannot reach browser debug port: {exc}")
    pages = [t for t in tabs if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
    if not pages:
        try:
            requests.put(f"{CDP_BASE}/json/new?about:blank", timeout=10)
            time.sleep(2)
            tabs = requests.get(f"{CDP_BASE}/json/list", timeout=10).json()
            pages = [t for t in tabs if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
        except Exception:  # noqa: BLE001
            pass
    if not pages:
        sys.exit("[fatal] no usable browser tab found")
    return pages[0]["webSocketDebuggerUrl"]


def normalize(url):
    """Unescape \\u0026 -> & and strip trailing backslashes."""
    url = url.replace("\\u0026", "&").replace("\\/", "/")
    return url.rstrip("\\")


def pick_quality(urls):
    """Return highest-quality URL. Skips audio-only streams."""
    candidates = [u for u in urls if "only_audio=1" not in u]
    for suffix in QUALITY_ORDER:
        for url in candidates:
            if suffix + ".flv" in url:
                return url, suffix
    return (candidates[0], "unknown") if candidates else (None, None)


def extract_stream(room_id, wait):
    ws_url = pick_tab()
    ws = websocket.create_connection(ws_url, timeout=40)
    counter = {"id": 1}

    def send(method, params=None):
        msg_id = counter["id"]
        counter["id"] += 1
        payload = {"id": msg_id, "method": method}
        if params:
            payload["params"] = params
        ws.send(json.dumps(payload))
        deadline = time.time() + 40
        while time.time() < deadline:
            resp = json.loads(ws.recv())
            if resp.get("id") == msg_id:
                return resp
        return {}

    send("Network.enable")
    send("Page.enable")
    live_url = f"https://live.douyin.com/{room_id}"
    print(f"[info] navigating to {live_url}", file=sys.stderr)
    send("Page.navigate", {"url": live_url})
    print(f"[info] waiting {wait}s for stream to load", file=sys.stderr)
    time.sleep(wait)

    result = send("Runtime.evaluate", {"expression": EXTRACT_JS, "returnByValue": True})
    ws.close()

    raw = result.get("result", {}).get("result", {}).get("value", "[]")
    try:
        urls = json.loads(raw)
    except Exception:  # noqa: BLE001
        urls = re.findall(r"https?://[^\"']+\.flv[^\"']*", raw)

    seen, unique = set(), []
    for url in urls:
        norm = normalize(url)
        if norm not in seen:
            seen.add(norm)
            unique.append(norm)
    return unique


def record(stream_url, duration, output, referer=None, alternatives=()):
    print(f"[info] recording {duration}s -> {output}", file=sys.stderr)
    for source in (stream_url, *alternatives):
        cmd = [
            "ffmpeg", "-y", *(["-referer", referer] if referer else []), "-i", source,
            "-t", str(duration), "-c", "copy", "-bsf:a", "aac_adtstoasc", output,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0 or "Error opening input" not in proc.stderr:
            break
    if proc.returncode != 0:
        sys.exit(f"[fatal] ffmpeg failed rc={proc.returncode}")
    if not os.path.exists(output) or os.path.getsize(output) < 100000:
        sys.exit("[fatal] output missing or too small; stream may have ended")
    size_mb = os.path.getsize(output) / 1024 / 1024
    print(f"[ok] recorded {output} ({size_mb:.1f} MB)", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--room", required=True, help="Douyin room ID or an official Douyin, Xiaohongshu or Bilibili live room URL")
    parser.add_argument("--duration", type=int, default=300, help="seconds, default 300")
    parser.add_argument("--output", help="output mp4 path")
    parser.add_argument("--wait", type=int, default=22, help="seconds to wait for stream")
    parser.add_argument("--codec", choices=("auto", "h264", "h265"), default="auto", help="Bilibili source codec")
    parser.add_argument("--extract-only", action="store_true")
    args = parser.parse_args()

    step = "extract" if args.extract_only else "record"
    with observe(step, "record_error") as fact:
        fact["reason"] = "stream_unavailable"
        try:
            platform, room_id = room_input(args.room)
            if args.codec != "auto" and platform != "bilibili":
                parser.error("--codec is supported for Bilibili rooms only")
            if platform == "douyin":
                urls = extract_stream(room_id, args.wait)
            else:
                observation = observe_room(args.room, args.wait, args.codec)
                if observation.get("status") == "not_live":
                    sys.exit("[fatal] room is offline")
                _, room_id = room_input(observation["page_url"])
                urls = observation["media_urls"]
        except LiveSourceError as exc:
            sys.exit("[fatal] " + str(exc))
        except (ValueError, OSError, requests.RequestException, websocket.WebSocketException) as exc:
            sys.exit("[fatal] unable to resolve live room: " + type(exc).__name__)
        if not urls:
            sys.exit("[fatal] no FLV stream found — room may be offline or login expired")

        best, quality = pick_quality(urls)
        if not best:
            sys.exit("[fatal] only audio-only streams found")
        print(f"[ok] found {len(urls)} stream(s), selected quality={quality}", file=sys.stderr)
        del fact["reason"]
        if args.extract_only:
            print(best)
            return

        prefix = "live" if platform == "douyin" else platform
        output = args.output or f"{prefix}_{room_id}_{args.duration}s.mp4"
        fact["requested_s"] = max(args.duration, 0)
        if platform == "douyin":
            record(best, args.duration, output)
        elif platform == "bilibili":
            alternatives = [url for url in dict.fromkeys(urls) if url != best and "only_audio=1" not in url]
            record(best, args.duration, output, referer=observation["page_url"], alternatives=alternatives)
        else:
            record(best, args.duration, output, referer=observation["page_url"])
        if (not disabled() and valid_id(os.getenv("DOUYIN_QC_FLOW_ID"))
                and valid_id(os.getenv("DOUYIN_QC_TASK_ID"))):
            actual = duration_ms(output)
            if actual:
                fact["actual_ms"] = actual
            else:
                fact.update(outcome="unknown", reason="duration_unverified")
    print(output)


if __name__ == "__main__":
    main()
