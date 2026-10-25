# YouTube-Transkript MCP-Server

## Test auf dem VPS (vor Coolify, ca. 3 Minuten)
Repo klonen, dann im Ordner yt-transcript-mcp:
    docker build -t yt-mcp .
    docker run --rm -d --name yt-mcp -p 8000:8000 -e MCP_PATH=/mcp-test yt-mcp
    curl -s -X POST localhost:8000/mcp-test \
      -H 'Content-Type: application/json' \
      -H 'Accept: application/json, text/event-stream' \
      -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
    docker stop yt-mcp
Erwartet: JSON mit dem Tool "get_transcript".

## Deployment mit Coolify
1. Repo: PushTheLimit23/tools, Ordner yt-transcript-mcp
2. Coolify: New Resource -> Public Repository -> Build Pack "Dockerfile", Base Directory: /yt-transcript-mcp
3. Port: 8000
4. Domain setzen, z. B. https://yt.deine-domain.de
5. Environment Variable setzen:
   MCP_PATH=/mcp-<zufaellige-zeichenkette>
   (z. B. mit `openssl rand -hex 8` auf dem VPS erzeugen)
6. Deploy.

## In claude.ai eintragen
Settings -> Connectors -> Add custom connector
URL: https://yt.deine-domain.de/mcp-<zufaellige-zeichenkette>
Danach ist der Connector auch in der iPad-App verfuegbar.

## Hinweise
- Die URL ist das einzige "Passwort". Nicht teilen.
- Falls YouTube die VPS-IP spaeter sperrt (Fehler RequestBlocked/IpBlocked):
  Residential-Proxy per WebshareProxyConfig in server.py nachruesten.
- requirements.txt pinnt mcp<2: In mcp 2.x wurde FastMCP umbenannt, der Code
  wuerde dort nicht starten.
- Fehler "421 Invalid Host header" hinter Coolify: DNS-Rebinding-Schutz des
  MCP-SDK. Dann Bescheid geben, ist eine Zeile Konfiguration.
