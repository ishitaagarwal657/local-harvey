"""
Optional public-web research helpers.
These are ONLY used when internet is available and the caller explicitly requests enrichment.
Core offline AI workflows never depend on this module.

Uses BeautifulSoup for simple page text extraction.
Playwright is optional and only attempted if installed + requested.
"""
from typing import Optional, Dict, Any
import re

try:
    import httpx
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


async def fetch_page_text(url: str, timeout: float = 10.0) -> Dict[str, Any]:
    """
    Fetch a public page and extract readable text.
    Returns structured result; never raises to the caller — errors are returned in the dict.
    """
    if not HAS_BS4:
        return {
            "ok": False,
            "error": "beautifulsoup4 / httpx not installed",
            "text": "",
            "title": ""
        }
    if not url or not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "invalid url", "text": "", "title": ""}

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            resp = await client.get(url, headers={
                "User-Agent": "LocalHarveyResearchBot/1.0 (educational; offline-first sales agent)"
            })
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            # Remove scripts/styles
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            title = (soup.title.string or "").strip() if soup.title else ""
            text = " ".join(soup.get_text(separator=" ").split())
            # Cap length so we don't blow the context window
            text = text[:4000]
            return {
                "ok": True,
                "url": str(resp.url),
                "title": title,
                "text": text,
                "status_code": resp.status_code
            }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "text": "",
            "title": ""
        }


def is_probably_online() -> bool:
    """Cheap connectivity check — used only to decide whether to attempt enrichment."""
    try:
        import socket
        socket.create_connection(("1.1.1.1", 53), timeout=1.5)
        return True
    except OSError:
        return False
