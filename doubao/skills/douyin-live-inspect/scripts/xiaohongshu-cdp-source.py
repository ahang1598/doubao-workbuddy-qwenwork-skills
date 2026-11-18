#!/usr/bin/env python3
"""Extract a browser FLV candidate; recording and inspection stay in Inspect."""
import argparse
import http.client
import json
import os
import re
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit, quote, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lite'))
from runtime.xiaohongshu_live import validate_url, validate_browser, candidate as valid_candidate, fetch, XiaohongshuLiveError


class SourceError(Exception):
    pass


def extract(source, port=9222, timeout=45, *, formal=False):
    source_page = validate_url(source)
    try:
        import websocket
    except ImportError:
        raise SourceError('CDP_DEPENDENCY_MISSING') from None
    deadline = time.monotonic() + timeout

    def remaining():
        left = deadline - time.monotonic()
        if left <= 0:
            raise SourceError('CDP_TIMEOUT')
        return min(8, left)

    def request(path, method='GET'):
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=remaining())
        try:
            connection.request(method, path)
            response = connection.getresponse()
            body = response.read(1024 * 1024 + 1)
            if response.status != 200 or len(body) > 1024 * 1024:
                raise SourceError('CDP_UNAVAILABLE')
            return json.loads(body)
        finally:
            connection.close()

    tabs = request('/json/list')
    tab = None
    for item in tabs:
        if item.get('type') != 'page' or not item.get('webSocketDebuggerUrl'):
            continue
        try:
            if validate_url(item.get('url')) == source_page:
                tab = item
                break
        except XiaohongshuLiveError:
            pass
    # Never navigate an unrelated user tab or launch another browser/profile.
    if tab is None:
        tab = request('/json/new?' + quote('about:blank', safe=''), 'PUT')
    endpoint = tab.get('webSocketDebuggerUrl', '')
    address = urlsplit(endpoint)
    if (address.scheme != 'ws' or address.hostname not in ('127.0.0.1', 'localhost', '::1')
            or address.port != port or address.username or address.password):
        raise SourceError('CDP_INVALID_TARGET')
    ws = websocket.create_connection(endpoint, timeout=remaining(), suppress_origin=True,
                                     http_no_proxy=['127.0.0.1', 'localhost', '::1'])
    sequence = 0
    network_urls = {}

    def call(method, params=None):
        nonlocal sequence
        sequence += 1
        ws.settimeout(remaining())
        ws.send(json.dumps({'id': sequence, 'method': method, 'params': params or {}}))
        while True:
            ws.settimeout(remaining())
            try:
                message = json.loads(ws.recv())
            except websocket.WebSocketTimeoutException:
                raise SourceError('CDP_TIMEOUT') from None
            if message.get('method') == 'Network.requestWillBeSent':
                url = message.get('params', {}).get('request', {}).get('url')
                if valid_candidate(url) and '1' not in parse_qs(urlsplit(url).query).get('only_audio', []):
                    network_urls[url] = None
                    if len(network_urls) > 64:
                        network_urls.pop(next(iter(network_urls)))
            if message.get('id') != sequence:
                continue
            if 'error' in message:
                raise SourceError('CDP_COMMAND_FAILED')
            return message.get('result', {})

    expression = Path(__file__).with_name('xiaohongshu-browser-observation.js').read_text()
    try:
        call('Network.enable')
        call('Page.enable')
        # Preserve the supplied share parameters for navigation, normalize only identity.
        navigation = call('Page.navigate', {'url': source})
        if navigation.get('errorText'):
            raise SourceError('CDP_NAVIGATION_FAILED')
        refresh_at = time.monotonic() + min(10, timeout / 3)
        refreshed = False
        while time.monotonic() < deadline:
            result = call('Runtime.evaluate', {'expression': expression, 'returnByValue': True})
            observation = result.get('result', {}).get('value')
            if isinstance(observation, str):
                try:
                    observation = json.loads(observation)
                except ValueError:
                    observation = None
            if not result.get('exceptionDetails') and isinstance(observation, dict):
                page = validate_url(observation.get('page_url'))
                if urlsplit(page).hostname != 'www.xiaohongshu.com':
                    raise SourceError('INVALID_BROWSER_SOURCE')
                if urlsplit(source_page).hostname != 'xhslink.com' and page != source_page:
                    raise SourceError('INVALID_BROWSER_SOURCE')
                if observation.get('status') == 'not_live':
                    ended = {'page_url': page, 'captured_at': observation.get('captured_at'), 'status': 'not_live'}
                    validate_browser(page, ended)
                    error = SourceError('XHS_NOT_LIVE')
                    error.browser_source = ended
                    raise error
                room = page.rsplit('/', 1)[-1]
                # Unfinished Fetch streams may never enter resource timing.
                urls = list(dict.fromkeys([*network_urls, *observation.get('media_urls', [])[:64]]))
                for url in urls:
                    if not valid_candidate(url) or not re.fullmatch(r'/live/' + room + r'(?:_[A-Za-z0-9_-]+)?\.flv', urlsplit(url).path):
                        continue
                    candidate = {key: observation.get(key) for key in ('page_url', 'captured_at', 'page_title')}
                    candidate['stream_url'] = url
                    try:
                        validate_browser(page, candidate)
                        if formal or fetch(url, timeout=remaining(), probe=True).get('ready'):
                            return {'browser_source': candidate}
                    except XiaohongshuLiveError:
                        continue
            # An existing MSE connection may produce neither new requests nor timing entries.
            if not refreshed and time.monotonic() >= refresh_at:
                network_urls.clear()
                call('Page.reload', {'ignoreCache': True})
                refreshed = True
            time.sleep(min(1, remaining()))
        raise SourceError('CDP_TIMEOUT')
    finally:
        ws.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--formal', action='store_true', help='Hand off the observed room stream for service-side inspection')
    parser.add_argument('--port', type=int, default=9222)
    parser.add_argument('--timeout', type=int, default=45)
    args = parser.parse_args()
    try:
        if not 1 <= args.port <= 65535 or not 1 <= args.timeout <= 120:
            raise SourceError('INVALID_INPUT')
        if Path(args.output).exists():
            raise SourceError('OUTPUT_EXISTS')
        result = extract(args.url, args.port, args.timeout, formal=args.formal)
        with os.fdopen(os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as output:
            json.dump(result, output, ensure_ascii=False)
        print(json.dumps({'ok': True, 'next_action': 'submit-browser-source'}))
        return 0
    except Exception as error:
        code = str(error) if isinstance(error, SourceError) else getattr(error, 'code', 'CDP_UNAVAILABLE')
        # CDP exceptions may contain signed URLs or page data; never print them.
        receipt = {'ok': False, 'error': {'code': code}}
        if code == 'XHS_NOT_LIVE':receipt['browser_source'] = error.browser_source
        print(json.dumps(receipt))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
