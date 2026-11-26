"""Bounded availability check for public registration URLs."""
import asyncio
import ipaddress
import socket
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
import requests


def canonical_url(value):
    """Keep meaningful query parameters, remove fragments and marketing trackers."""
    parts = urlsplit(value)
    query = [(key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
             if not key.lower().startswith('utm_') and key.lower() not in {'fbclid','gclid','yclid','ref_src'}]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip('/') or '/', urlencode(sorted(query)), ''))

def public_url(url):
    try:
        parts = urlsplit(url)
        if parts.scheme not in ('https', 'http') or not parts.hostname or parts.username or parts.password:
            return False
        addresses = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == 'https' else 80))
        return bool(addresses) and all(ipaddress.ip_address(item[4][0]).is_global for item in addresses)
    except (ValueError, OSError):
        return False

def _check(url):
    try:
        for _ in range(4):
            if not public_url(url): return False
            with requests.get(url, timeout=(3, 5), stream=True, allow_redirects=False,
                              headers={'User-Agent': 'UserFlow/2.0'}) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    url = urljoin(url, response.headers.get('Location', ''))
                    continue
                return 200 <= response.status_code < 300
        return False
    except requests.RequestException:
        return False

async def check_link(url):
    try:
        return await asyncio.wait_for(asyncio.to_thread(_check, url), timeout=12)
    except TimeoutError:
        return False
