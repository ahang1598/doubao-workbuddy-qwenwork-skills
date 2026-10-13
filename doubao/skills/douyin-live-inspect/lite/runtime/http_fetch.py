# Adapted from skills_live_inspect_lite/runtime/http_fetch.py; content-only migration.
"""Isolated stdlib HTTP worker; the parent enforces a hard process deadline.

stdin/stdout are bounded JSON envelopes. No credentials, URLs or server error
text are emitted on failures. Redirects are returned for parent validation.
"""
import base64
import json
import math
import ipaddress
import os
import socket
import ssl
from urllib.parse import urlsplit
import sys
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

MAX_INPUT_BYTES = 65_536
MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_HEADER_BYTES = 8192


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _https_context():
    context = ssl.create_default_context()
    if (sys.platform == 'darwin' and not os.environ.get('SSL_CERT_FILE')
            and not os.environ.get('SSL_CERT_DIR')
            and context.cert_store_stats()['x509_ca'] == 0
            and os.path.isfile('/etc/ssl/cert.pem')):
        # Some python.org macOS installs have an empty OpenSSL store; retain TLS verification.
        context = ssl.create_default_context(cafile='/etc/ssl/cert.pem')
    return context


def fetch(request):
    url = request['url']
    headers = request['headers']
    timeout = float(request['timeout'])
    image = request.get('content_kind') == 'image'
    maximum = min(int(request['maximum_bytes']), MAX_IMAGE_BYTES if image else MAX_BODY_BYTES)
    if image:
        target = urlsplit(url)
        if target.scheme != 'https' or not target.hostname or target.username or target.password or target.port not in (None,443):
            raise ValueError('invalid image address')
        addresses = socket.getaddrinfo(target.hostname,443,type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
            raise ValueError('invalid image address')
        headers = {}  # Never send host credentials to a result URL.
    if (not isinstance(url, str) or len(url) > 8192 or not isinstance(headers, dict)
            or not math.isfinite(timeout) or timeout <= 0 or maximum < 0):
        raise ValueError('invalid worker request')
    try:
        response = build_opener(_NoRedirect(), HTTPSHandler(context=_https_context())).open(
            Request(url, headers=headers), timeout=timeout)
    except HTTPError as error:
        response = error
    with response:
        # Only these headers are consumed by the resolver. Bound each field so
        # even an unusual remote response cannot expand the output envelope.
        output_headers = {}
        for name in ('content-type', 'content-length', 'location'):
            value = response.headers.get(name)
            if value is not None:
                if len(value.encode('utf-8')) > MAX_HEADER_BYTES:
                    return {'error': 'DOUYIN_PAGE_UNAVAILABLE'}
                output_headers[name] = value
        result = {'status': response.status, 'headers': output_headers, 'body': ''}
        content_type = output_headers.get('content-type', '').lower()
        if not 200 <= response.status < 300 or not any(t in content_type for t in (('image/jpeg','image/png') if image else ('text/html','application/xhtml+xml'))):
            return result
        try:
            declared = int(output_headers.get('content-length', 0))
        except ValueError:
            declared = 0
        if declared > maximum:
            return {'error': 'DOUYIN_PAGE_UNAVAILABLE'}
        # A stalled DNS lookup, response header or body is bounded by the
        # parent's subprocess deadline, independently of socket timeout resets.
        body = response.read(maximum + 1)
        if len(body) > maximum:
            return {'error': 'DOUYIN_PAGE_UNAVAILABLE'}
        result['body'] = base64.b64encode(body).decode('ascii')
        return result


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError('oversized worker request')
        result = fetch(json.loads(raw))
    except Exception:
        result = {'error': 'DOUYIN_FETCH_FAILED'}
    sys.stdout.write(json.dumps(result, ensure_ascii=True, separators=(',', ':')))


if __name__ == '__main__':
    main()
