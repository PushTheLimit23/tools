"""YouTube-Transkript MCP-Server (Streamable HTTP) fuer claude.ai Custom Connector."""

import json
import os
import re
import urllib.parse
import urllib.request

from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi

# Geheimer Pfad als einfacher Zugriffsschutz, z. B. /mcp-7f3k9x2q
_raw_path = os.environ.get("MCP_PATH", "/mcp").strip().strip("'\"").strip("/")
SECRET_PATH = "/" + (_raw_path or "mcp")  # fuehrender "/" wird ergaenzt, falls er fehlt

mcp = FastMCP(
    "youtube-transcript",
    host="0.0.0.0",
    port=int(os.environ.get("PORT", "8000")),
    streamable_http_path=SECRET_PATH,
    stateless_http=True,
)

ytt = YouTubeTranscriptApi()

ID_PATTERN = re.compile(
    r"(?:v=|youtu\.be/|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{11})"
)


def extract_video_id(url_or_id: str) -> str:
    """Akzeptiert alle gaengigen YouTube-Links oder direkt die 11-stellige ID."""
    s = url_or_id.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", s):
        return s
    m = ID_PATTERN.search(s)
    if not m:
        raise ValueError(f"Keine YouTube-Video-ID gefunden in: {s}")
    return m.group(1)


def fmt_time(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def fetch_metadata(video_id: str) -> dict:
    """Titel und Kanal ueber die oEmbed-Schnittstelle von YouTube (ohne API-Key).
    Fehler hier duerfen das Transkript nicht verhindern -> leeres dict."""
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    api = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(watch_url, safe="")
    try:
        req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
        return {
            "title": data.get("title"),
            "channel": data.get("author_name"),
            "channel_url": data.get("author_url"),
            "url": watch_url,
        }
    except Exception:
        return {"url": watch_url}


@mcp.tool()
def get_transcript(url: str, languages: list[str] | None = None) -> str:
    """Holt Titel, Kanal und Transkript eines YouTube-Videos. Das Transkript kommt
    als Fliesstext mit Zeitmarken (ca. jede Minute), damit auf Stellen im Video
    verwiesen werden kann.

    Args:
        url: YouTube-Link (watch, youtu.be, shorts, live) oder Video-ID.
        languages: Bevorzugte Sprachen in Reihenfolge, Standard ["de", "en"].
    """
    video_id = extract_video_id(url)
    langs = languages or ["de", "en"]
    fetched = ytt.fetch(video_id, languages=langs)

    blocks: list[str] = []
    current: list[str] = []
    block_start = 0.0
    for snippet in fetched:
        if current and snippet.start - block_start >= 60:
            blocks.append(f"[{fmt_time(block_start)}] " + " ".join(current))
            current = []
        if not current:
            block_start = snippet.start
        text = snippet.text.replace("\n", " ").strip()
        if text:
            current.append(text)
    if current:
        blocks.append(f"[{fmt_time(block_start)}] " + " ".join(current))

    meta = fetch_metadata(video_id)
    header = (
        f"Titel: {meta.get('title') or 'unbekannt'}\n"
        f"Kanal: {meta.get('channel') or 'unbekannt'}"
        + (f" ({meta['channel_url']})" if meta.get("channel_url") else "")
        + "\n"
        f"URL: {meta['url']}\n"
        f"Video-ID: {video_id}\n"
        f"Sprache: {fetched.language} "
        f"({'automatisch generiert' if fetched.is_generated else 'manuell'})\n\n"
    )
    return header + "\n\n".join(blocks)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
