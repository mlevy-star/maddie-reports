#!/bin/bash
set -euo pipefail
TODAY=$(TZ="America/New_York" date +"%B %d, %Y")
PROMPT=$(sed "s/{{TODAY}}/$TODAY/g" ~/maddie-reports/narvar_daily.md)
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting Narvar OTP daily run for $TODAY"
claude -p "$PROMPT"
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Run complete"
