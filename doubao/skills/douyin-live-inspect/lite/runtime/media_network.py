"""Validate media DNS, including Doubao's managed cloud egress addresses."""
import ipaddress
import os
import socket


def resolve_addresses(host, port, *args, resolver=socket.getaddrinfo, **kwargs):
    addresses = resolver(host, port, *args, **kwargs)
    host = host.lower().rstrip('.')
    platform_host = (host in {'www.xiaohongshu.com', 'live-room.xiaohongshu.com', 'xhslink.com', 'live.bilibili.com', 'api.live.bilibili.com', 'b23.tv'}
                     or host.endswith(('.douyincdn.com', '.xhscdn.com', '.bilivideo.com')))
    cloud = (os.environ.get('CUA_USE_ISOLATED_ENV') != '0'
             and (any(key.startswith('DOUBAO_OFFICE_') for key in os.environ)
                  or bool(os.environ.get('DOUBAO_SANDBOX_TYPE')))
             and (os.environ.get('CUA_USE_ISOLATED_ENV') == '1'
                  or os.environ.get('DOUBAO_SANDBOX_TYPE') == 'SaaS'))
    gateways = (ipaddress.ip_network('100.64.0.0/10'), ipaddress.ip_network('fc00::/7'))
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_global and not ip.is_multicast and not ip.is_reserved:
            continue
        # Only supported platform names may use the host's synthetic egress mapping.
        if cloud and platform_host and any(ip.version == network.version and ip in network for network in gateways):
            continue
        raise socket.gaierror('media_address_rejected')
    if not addresses:
        raise socket.gaierror('media_address_rejected')
    return addresses
