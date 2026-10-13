#!/usr/bin/env python3
"""Search Douyin for live rooms by keyword via Chrome DevTools Protocol.

Given an account name or brand name, opens the Douyin search page (live tab),
scrolls to load results, and extracts all currently-live rooms with their
room_id, account name, live title, and verification badge status.

Usage:
    python3 search_live.py "某品牌官方旗舰店"
    python3 search_live.py "某品牌名" --json
    python3 search_live.py "某品牌名" --scroll 5

Requires: websocket-client, requests, a Chrome running with
--remote-debugging-port=9222 and a logged-in Douyin session.
"""
import argparse
import json
import re
import sys
import time
import urllib.parse

import requests
import websocket

CDP_BASE = "http://127.0.0.1:9222"

# JS to extract live room cards from the search results page.
# Tries multiple strategies because Douyin's DOM structure changes occasionally.
EXTRACT_JS = r"""
(function() {
    var results = [];
    var seen = {};

    // Strategy 1: find all anchors linking to live.douyin.com/<digits>
    var anchors = document.querySelectorAll('a[href*="live.douyin.com/"]');
    for (var i = 0; i < anchors.length; i++) {
        var a = anchors[i];
        var href = a.href || a.getAttribute('href') || '';
        var m = href.match(/live\.douyin\.com\/(\d+)/);
        if (!m) continue;
        var roomId = m[1];
        if (seen[roomId]) continue;

        // Walk up to find a card-like container
        var card = a;
        for (var up = 0; up < 6; up++) {
            if (!card.parentElement) break;
            card = card.parentElement;
            var text = card.innerText || '';
            if (text.length > 20 && text.length < 500) break;
        }

        var cardText = (card.innerText || '').trim();
        var lines = cardText.split('\n').map(function(s){return s.trim();}).filter(Boolean);

        // Account name: usually near the top of the card, may contain "· 正在直播"
        var name = '';
        var title = '';
        var isVerified = false;

        // Look for verification badge (blue V) in the card
        if (card.querySelector('[class*="verify"], [class*="Verified"], svg[class*="verify"]')) {
            isVerified = true;
        }

        // Try to find name: usually a short line before "正在直播"
        for (var j = 0; j < lines.length; j++) {
            var line = lines[j];
            if (line.indexOf('正在直播') !== -1 || line.indexOf('直播中') !== -1) {
                // Name is often on the same line before the dot, or the previous line
                var parts = line.split(/[·•]/);
                if (parts.length > 1 && parts[0].trim().length > 0) {
                    name = parts[0].trim();
                } else if (j > 0) {
                    name = lines[j-1];
                }
                // Title is usually a few lines after
                for (var k = j+1; k < lines.length && k < j+5; k++) {
                    if (lines[k].length > 4 && lines[k].indexOf('正在直播') === -1
                        && lines[k].indexOf('直播中') === -1
                        && lines[k].indexOf('人观看') === -1
                        && lines[k].indexOf('点赞') === -1) {
                        title = lines[k];
                        break;
                    }
                }
                break;
            }
        }

        // Fallback: use anchor text or first meaningful line
        if (!name) {
            name = (a.innerText || '').trim().split('\n')[0] || lines[0] || '';
        }
        if (!title && lines.length > 1) {
            for (var t = 0; t < lines.length; t++) {
                if (lines[t] !== name && lines[t].length > 4) {
                    title = lines[t];
                    break;
                }
            }
        }

        seen[roomId] = true;
        results.push({
            room_id: roomId,
            name: name.substring(0, 40),
            title: (title || '').substring(0, 80),
            verified: isVerified,
            href: href.split('?')[0]
        });
    }

    return JSON.stringify(results);
})()
"""


def pick_tab():
    """Return webSocketDebuggerUrl of a usable page tab."""
    try:
        tabs = requests.get(f"{CDP_BASE}/json/list", timeout=10).json()
    except Exception as exc:
        sys.exit(f"[fatal] cannot reach browser debug port: {exc}")
    pages = [t for t in tabs if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
    if not pages:
        sys.exit("[fatal] no usable browser tab found — is Chrome running with --remote-debugging-port=9222?")
    return pages[0]["webSocketDebuggerUrl"]


def cdp_send(ws, counter, method, params=None):
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


def search_live(keyword, scroll_rounds=4, wait_between=2):
    """Search Douyin live tab and return list of live room dicts."""
    ws_url = pick_tab()
    ws = websocket.create_connection(ws_url, timeout=60)
    counter = {"id": 1}

    cdp_send(ws, counter, "Page.enable")
    cdp_send(ws, counter, "Runtime.enable")

    search_url = f"https://www.douyin.com/search/{urllib.parse.quote(keyword)}?type=live"
    print(f"[info] searching: {search_url}", file=sys.stderr)
    cdp_send(ws, counter, "Page.navigate", {"url": search_url})

    # Wait for results to load
    print("[info] waiting for results to load...", file=sys.stderr)
    time.sleep(5)

    # Scroll to load more results (virtual list removes off-screen DOM,
    # so we scroll incrementally and collect after each scroll)
    all_results = {}
    for i in range(scroll_rounds):
        # Extract current visible results
        result = cdp_send(ws, counter, "Runtime.evaluate",
                          {"expression": EXTRACT_JS, "returnByValue": True})
        raw = result.get("result", {}).get("result", {}).get("value", "[]")
        try:
            items = json.loads(raw)
        except Exception:
            items = []
        for item in items:
            all_results[item["room_id"]] = item

        if i < scroll_rounds - 1:
            # Scroll down
            cdp_send(ws, counter, "Runtime.evaluate", {
                "expression": "window.scrollBy(0, window.innerHeight * 1.5);"
            })
            time.sleep(wait_between)

    # Final extraction after last scroll
    result = cdp_send(ws, counter, "Runtime.evaluate",
                      {"expression": EXTRACT_JS, "returnByValue": True})
    raw = result.get("result", {}).get("result", {}).get("value", "[]")
    try:
        items = json.loads(raw)
    except Exception:
        items = []
    for item in items:
        all_results[item["room_id"]] = item

    ws.close()
    return list(all_results.values())


def main():
    parser = argparse.ArgumentParser(description="Search Douyin live rooms by keyword")
    parser.add_argument("keyword", help="account name or brand name to search")
    parser.add_argument("--json", action="store_true", help="output JSON")
    parser.add_argument("--scroll", type=int, default=4,
                        help="number of scroll rounds to load more results (default 4)")
    args = parser.parse_args()

    results = search_live(args.keyword, scroll_rounds=args.scroll)

    if not results:
        print("[info] no live rooms found for this keyword", file=sys.stderr)
        if args.json:
            print(json.dumps([], ensure_ascii=False))
        return

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    # Pretty print
    print(f"\n找到 {len(results)} 个在播直播间：\n")
    for i, r in enumerate(results, 1):
        v = " [蓝V]" if r["verified"] else ""
        print(f"  {i}. {r['name']}{v}")
        print(f"     room_id: {r['room_id']}")
        print(f"     标题: {r['title'] or '(未获取到)'}")
        print(f"     链接: {r['href']}")
        print()


if __name__ == "__main__":
    main()
