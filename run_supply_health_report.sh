#!/bin/bash
set -euo pipefail
TODAY=$(TZ="America/New_York" date +"%B %d, %Y")
PROMPT=$(sed "s/{{TODAY}}/$TODAY/g" ~/maddie-reports/weekly_supply_health_report.md)
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting Weekly Supply Health Report for $TODAY"
claude -p "$PROMPT" --allowedTools "mcp__Hex__*,mcp__Slack__*,Bash"
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Run complete"
