#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$DIR/bin/cloudflared"
LOG="$DIR/tunnel.log"

if pgrep -f "cloudflared tunnel --url http://localhost:5173" > /dev/null 2>&1; then
  echo "Cloudflare Tunnel is already running."
else
  echo "Starting Cloudflare Tunnel..."
  nohup "$BIN" tunnel --url http://localhost:5173 > "$LOG" 2>&1 &
  sleep 4
fi

URL=$(grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' "$LOG" | head -1)
if [ -n "$URL" ]; then
  echo "=========================================================="
  echo " VeriTrace AI Live Public Deployment URL:"
  echo " $URL"
  echo "=========================================================="
else
  echo "Waiting for tunnel URL... Check $LOG"
fi
