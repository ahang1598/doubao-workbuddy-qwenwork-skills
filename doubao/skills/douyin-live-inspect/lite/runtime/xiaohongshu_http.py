"""有界、无 Cookie 的小红书 HTTP 子进程；只输出脱敏错误。"""
import http.client
import ipaddress
import json
import socket
import ssl
import sys
from urllib.parse import urlsplit, urljoin
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from http_fetch import _https_context, failure_kind


def flv_media(data):
    if len(data)<13 or data[:4]!=b'FLV\x01':return False
    offset=int.from_bytes(data[5:9],'big')
    if not 9<=offset<=1024:return False
    cursor=offset+4;tracks=set()
    while cursor+11<=len(data):
        size=int.from_bytes(data[cursor+1:cursor+4],'big');end=cursor+11+size
        if end+4>len(data):break
        if int.from_bytes(data[end:end+4],'big')!=11+size:return False
        if size and data[cursor]&31 in (8,9):tracks.add(data[cursor]&31)
        if tracks=={8,9}:return True
        cursor=end+4
    return False


def request(value, timeout, probe=False):
    for hop in range(4):
        u=urlsplit(value)
        hosts={'www.xiaohongshu.com','xhslink.com','live-room.xiaohongshu.com'}
        if (u.scheme not in ('http','https') or u.username or u.password or u.port not in (None,80,443)
                or (not probe and (u.scheme!='https' or u.hostname not in hosts))):raise ValueError()
        addresses=socket.getaddrinfo(u.hostname,u.port or (443 if u.scheme=='https' else 80),type=socket.SOCK_STREAM)
        ips=[ipaddress.ip_address(a[4][0]) for a in addresses]
        if not ips or any(not ip.is_global or ip.is_multicast or ip.is_reserved for ip in ips):raise ValueError()
        selected=addresses[0]
        sock=socket.socket(selected[0],socket.SOCK_STREAM);sock.settimeout(timeout)
        conn=None
        try:
            sock.connect(selected[4])
            if u.scheme=='https':sock=_https_context().wrap_socket(sock,server_hostname=u.hostname)
            conn=http.client.HTTPConnection(u.hostname,timeout=timeout);conn.sock=sock
            conn.request('GET',u.path+('?' + u.query if u.query else ''),headers={'User-Agent':'Mozilla/5.0','Accept':'application/json,text/html,*/*'})
            response=conn.getresponse()
            location=response.getheader('location')
            if probe and response.status in (301,302,303,307,308) and location:
                value=urljoin(value,location);continue
            if not probe and response.status in (301,302,303,307,308):
                return {'status':response.status,'location':location,'body':''}
            if response.status!=200:return {'status':response.status,'body':''}
            data=bytearray();maximum=1024*1024 if probe else 2*1024*1024
            while len(data)<=maximum:
                chunk=response.read1(min(16384,maximum+1-len(data)))
                if not chunk:break
                data.extend(chunk)
                if probe and flv_media(data):return {'status':200,'ready':True}
                if probe and len(data)>=3 and data[:3]!=b'FLV':raise ValueError()
            if len(data)>maximum:raise ValueError()
            return {'status':response.status,'body':data.decode('utf-8')} if not probe else {'status':200,'ready':False}
        finally:
            if conn:conn.close()
            sock.close()
    raise ValueError()


if __name__=='__main__':
    try:
        raw=sys.stdin.buffer.read(65537)
        if len(raw)>65536:raise ValueError()
        value=json.loads(raw)
        result=request(value['url'],value['timeout'],value.get('probe',False))
    except Exception as error:result={'error':'XHS_FETCH_FAILED','diagnostic':{'kind':failure_kind(error)}}
    print(json.dumps(result))
