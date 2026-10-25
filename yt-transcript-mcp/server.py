"""YouTube-Transkript MCP-Server (Streamable HTTP) fuer claude.ai Custom Connector."""

import os
import re

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


@mcp.tool()
def get_transcript(url: str, languages: list[str] | None = None) -> str:
    """Holt das Transkript eines YouTube-Videos als Fliesstext mit Zeitmarken
    (ca. jede Minute), damit auf Stellen im Video verwiesen werden kann.

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

    header = (
        f"Video-ID: {video_id}\n"
        f"Sprache: {fetched.language} "
        f"({'automatisch generiert' if fetched.is_generated else 'manuell'})\n\n"
    )
    return header + "\n\n".join(blocks)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
