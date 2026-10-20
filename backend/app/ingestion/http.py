import hashlib

import httpx


def download(url: str, *, timeout: float = 30.0) -> tuple[bytes, str]:
    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    content = response.content
    return content, hashlib.sha256(content).hexdigest()
