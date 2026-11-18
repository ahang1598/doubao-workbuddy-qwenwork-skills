"""Resolve a QC room input and observe a fresh, isolated browser tab."""
import json
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import requests
import websocket

CDP = "http://127.0.0.1:9222"
ROOMS = {
    "live.douyin.com": ("douyin", r"/([0-9]+)/?"),
    "live.bilibili.com": ("bilibili", r"/([1-9][0-9]*)/?"),
    "www.xiaohongshu.com": ("xiaohongshu", r"/livestream/(?:dynpath[A-Za-z0-9]+/)?([0-9]+)/?"),
}
SHORT = {"b23.tv": ("bilibili", r"/[A-Za-z0-9]+/?"),
         "xhslink.com": ("xiaohongshu", r"/[A-Za-z0-9_/-]+")}


class LiveSourceError(ValueError):
    """A fixed diagnostic safe for chat and logs."""


def room_input(value):
    if re.fullmatch(r"[0-9]+", value):
        return "douyin", value
    u = urlsplit(value)
    if (len(value) > 8192 or re.search(r"[\x00-\x20\\]", value) or u.username is not None
            or u.password is not None or u.port not in (None, 443)):
        raise LiveSourceError("Invalid live room link")
    if u.scheme != "https" and not (u.scheme == "http" and u.hostname == "xhslink.com"):
        raise LiveSourceError("Expected an official live room link")
    if u.hostname in ROOMS:
        platform, pattern = ROOMS[u.hostname]
        match = re.fullmatch(pattern, u.path)
        if match:
            return platform, match[1]
    if u.hostname in SHORT:
        platform, pattern = SHORT[u.hostname]
        if re.fullmatch(pattern, u.path):
            return platform, None
    raise LiveSourceError("Unsupported live room link")


def xhs_media_room(candidate):
    if not isinstance(candidate, str) or len(candidate) > 8192:
        return None
    try:
        u = urlsplit(candidate)
        if (u.scheme not in ("http", "https") or not (u.hostname or "").endswith(".xhscdn.com")
                or u.username is not None or u.password is not None or u.fragment
                or u.port not in (None, 80, 443) or "1" in parse_qs(u.query).get("only_audio", [])):
            return None
        match = re.fullmatch(r"/live/([0-9]+)(?:_[A-Za-z0-9_-]+)?\.flv", u.path)
        return match[1] if match else None
    except ValueError:
        return None


def observe_room(value, wait=22, codec="auto"):
    platform, expected = room_input(value)
    expression = Path(__file__).with_name(platform + "-browser-observation.js").read_text(encoding="utf-8")
    if platform == "bilibili":
        expression += "(" + json.dumps(codec) + ")"
    response = requests.put(CDP + "/json/new?about:blank", timeout=5)
    response.raise_for_status()
    tab = response.json()
    try:
        ws = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=20, suppress_origin=True)
        try:
            seq = 0
            network_media = {}
            deadline = time.monotonic() + max(1, wait)

            def call(method, params):
                nonlocal seq
                seq += 1
                ws.send(json.dumps(dict(id=seq, method=method, params=params)))
                while True:
                    if platform == "xiaohongshu":
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise LiveSourceError("No live FLV observed before timeout")
                        ws.settimeout(remaining)
                    reply = json.loads(ws.recv())
                    if reply.get("method") == "Network.requestWillBeSent":
                        candidate = reply["params"]["request"]["url"]
                        room = xhs_media_room(candidate)
                        if room and (not expected or room == expected):
                            network_media[candidate] = room
                            if len(network_media) > 64:
                                del network_media[next(iter(network_media))]
                    if reply.get("id") == seq:
                        if "error" in reply:
                            raise LiveSourceError("Browser command failed")
                        return reply["result"]

            page = value.replace("http://xhslink.com/", "https://xhslink.com/", 1)
            if platform == "xiaohongshu":
                call("Network.enable", {})
            if call("Page.navigate", {"url":page}).get("errorText"):
                raise LiveSourceError("Live room navigation failed")
            while True:
                result = call("Runtime.evaluate", dict(expression=expression, awaitPromise=True, returnByValue=True))
                data = result.get("result", {}).get("value")
                if isinstance(data, dict):
                    actual_platform, actual_room = room_input(data["page_url"])
                    if actual_platform != platform or not actual_room or (expected and actual_room != expected):
                        raise LiveSourceError("Live room identity mismatch")
                    if data.get("status") == "not_live":
                        return data
                    if platform == "xiaohongshu":
                        urls = [url for url, room in network_media.items() if room == actual_room]
                        urls.extend(url for url in data.get("media_urls", [])
                                    if xhs_media_room(url) == actual_room and url not in urls)
                    else:
                        urls = []
                        for candidate in data.get("media_urls", []):
                            u = urlsplit(candidate)
                            if (u.scheme in ("http", "https") and (u.hostname or "").endswith(".bilivideo.com")
                                    and u.username is None and u.password is None and not u.fragment
                                    and u.port in (None, 80, 443) and u.path.lower().endswith(".flv")):
                                urls.append(candidate)
                    if urls:
                        data["media_urls"] = urls
                        return data
                error = result.get("result", {}).get("description", "")
                if codec != "auto" and "BILI_STREAM_UNAVAILABLE" in error:
                    raise LiveSourceError(f"No {codec} FLV available for this Bilibili room")
                if "BILI_REPLAY_UNSUPPORTED" in error:
                    raise LiveSourceError("Bilibili replay is not a live broadcast")
                if time.monotonic() >= deadline:
                    raise LiveSourceError("No live FLV observed; check the room and browser login")
                time.sleep(1)
        finally:
            ws.close()
    finally:
        try:
            requests.get(CDP + "/json/close/" + tab["id"], timeout=3)
        except requests.RequestException:
            pass
