#!/usr/bin/env python3
"""Probe Douyin live rooms for online status, concurrently.

Usage:
    python3 probe_live.py <room_id>[,<room_id>...]
    python3 probe_live.py --file rooms.csv

CSV format (no header needed): room_id,account_name
Output: one line per room -> room_id | name | LIVE/OFF/ERR | title
"""
import argparse
import concurrent.futures
import re
import sys

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/146.0.7680.31 Safari/537.36"
    ),
    "Referer": "https://live.douyin.com/",
}
PROXIES = {"http": "http://127.0.0.1:8118", "https": "http://127.0.0.1:8118"}


def probe(item):
    room_id, name = item
    url = f"https://live.douyin.com/{room_id}"
    for attempt in range(2):
        try:
            resp = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=20)
            html = resp.text
            is_live = ('"status":2' in html) or (".flv" in html)
            title = ""
            match = re.search(r'"title":"([^"]{2,60})"', html)
            if match:
                title = match.group(1)
            return (room_id, name, "LIVE" if is_live else "OFF", title[:40])
        except Exception as exc:  # noqa: BLE001
            if attempt == 1:
                return (room_id, name, "ERR", str(exc)[:50])
    return (room_id, name, "ERR", "unknown")


def load_rooms(args):
    if args.file:
        rooms = []
        with open(args.file, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split(",")]
                room_id = parts[0]
                name = parts[1] if len(parts) > 1 else room_id
                rooms.append((room_id, name))
        return rooms
    return [(rid.strip(), rid.strip()) for rid in args.rooms.split(",") if rid.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("rooms", nargs="?", default="", help="comma separated room ids")
    parser.add_argument("--file", help="CSV file: room_id,account_name")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    rooms = load_rooms(args)
    if not rooms:
        parser.error("provide room ids or --file")

    live_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(probe, rooms):
            print(" | ".join(str(x) for x in result))
            if result[2] == "LIVE":
                live_count += 1
    print(f"\n[summary] {live_count}/{len(rooms)} rooms LIVE", file=sys.stderr)


if __name__ == "__main__":
    main()
