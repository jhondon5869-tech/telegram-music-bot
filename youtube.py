"""YouTube search and metadata extraction via yt-dlp."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import yt_dlp

log = logging.getLogger(__name__)

# Shared yt-dlp options — audio-only, no playlist expansion
_YDL_OPTS: dict[str, Any] = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "extract_flat": False,
}


def _search_sync(query: str) -> dict[str, Any] | None:
    """Blocking yt-dlp search — run in a thread pool."""
    search_target = query if query.startswith(("http://", "https://")) else f"ytsearch1:{query}"

    try:
        with yt_dlp.YoutubeDL(_YDL_OPTS) as ydl:
            info = ydl.extract_info(search_target, download=False)
    except Exception as exc:
        log.error("yt-dlp failed for %r: %s", query, exc)
        return None

    if not info:
        return None

    # ytsearch returns a playlist-like dict with entries
    if "entries" in info:
        entries = info.get("entries") or []
        if not entries:
            return None
        info = entries[0]

    webpage_url = info.get("webpage_url") or info.get("url")
    if not webpage_url:
        return None

    return {
        "title": info.get("title", "Unknown"),
        "url": webpage_url,
        "duration": info.get("duration") or 0,
        "thumbnail": info.get("thumbnail") or "",
        "uploader": info.get("uploader") or "Unknown",
    }


async def search_youtube(query: str) -> dict[str, Any] | None:
    """Search YouTube (or resolve a direct URL) and return track metadata."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _search_sync, query.strip())


def format_duration(seconds: int) -> str:
    """Format seconds as M:SS."""
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}:{secs:02d}"
