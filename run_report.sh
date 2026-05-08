#!/usr/bin/env bash
# run_report.sh — Weekly Publisher Health Report runner
# Called by cron every day at 9 AM ET. Invokes Claude Code CLI with full report spec.
set -euo pipefail

cd "$(dirname "$0")"

TODAY=$(date +%Y-%m-%d)

CURRENT_END=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null \
  || date -v-1d +%Y-%m-%d)          # macOS fallback
CURRENT_START=$(date -d "7 days ago" +%Y-%m-%d 2>/dev/null \
  || date -v-7d +%Y-%m-%d)
PRIOR_END=$(date -d "8 days ago" +%Y-%m-%d 2>/dev/null \
  || date -v-8d +%Y-%m-%d)
PRIOR_START=$(date -d "14 days ago" +%Y-%m-%d 2>/dev/null \
  || date -v-14d +%Y-%m-%d)

claude --allowedTools "mcp__Hex__*,mcp__Slack__*,mcp__Gmail__*,Bash" -p "
Run the Weekly Publisher Health Report for today, ${TODAY}.
All config, thresholds, and formulas are in weekly_publisher_health_report.py.

Rolling windows (always use these exact dates — do not re-derive):
  current : ${CURRENT_START} through ${CURRENT_END}
  prior   : ${PRIOR_START} through ${PRIOR_END}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — RPL by Page Type, WoW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Query the Supply Performance Hex project (hex_supply_performance_project in config).
Run three separate analyses:

SECTION A — All Publishers (excl. Mindbody, Gopuff, BevMo)
  Source: FCT_SESSIONS joined to FCT_BRAND_SESSIONS on session_id.
  Page types (exclude MODAL): THANK_YOU→TYP, ORDER_STATUS→OSP,
    ORDER_TRACKING→OTP, SUPPORT_CENTER→Support.
  For each page type, compute:
    - prior_rpl  = sum(billable_amount) / sum(sessions_with_widget_display)  [prior window]
    - current_rpl = same formula for current window
    - wow_delta  = (current_rpl - prior_rpl) / nullif(prior_rpl, 0)
  Also compute DFL WoW direction (sessions_with_widget_display up or down per page type).
  DFLs flat/up + spend fell → demand-side. DFLs fell → supply-side.

SECTION B — Gopuff / BevMo
  Same FCT_SESSIONS + FCT_BRAND_SESSIONS, filtered to Gopuff and BevMo publishers.
  Same page-type breakdown and WoW delta. Show publisher name per row.

SECTION C — Mindbody (custom pipeline)
  Source: reporting.event + reporting.combined_cpc_cpa_ad_spend_revenue.
  1. Dedup: use lag() over (partition by order_id order by event_created_at);
     keep only first-event rows (lag IS NULL).
  2. Moroccanoil CPM: for widget_viewable_threshold_brand_display events where
     brand = Moroccanoil, add impressions * \$0.10 to billable_amount.
  3. Group action types:
     BOOKING GROUP  = booking + upcoming_booking
     PURCHASE GROUP = purchase + booking_and_purchase + purchase_and_booking
  4. Compute RPL and WoW delta for each group.
  5. Note whether move is spend-side (ad_ops session count flat/up, spend fell)
     or volume-side (session count fell).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — Network-Wide Advertiser Signals
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Join FCT_BRAND_SESSIONS to FCT_SESSIONS on session_id. Exclude Mindbody publishers.
GROUP BY brand_name, is_nea, brand_display_context.
IMPORTANT: brand_display_context must be in GROUP BY to prevent double-counting
Hero vs. Multiple placement spend for the same brand.

For each brand compute:
  - total_prior_spend   = sum(billable_amount) in prior window
  - total_current_spend = sum(billable_amount) in current window
  - spend_delta         = total_current_spend - total_prior_spend
  - publisher_count     = distinct publishers where abs(that publisher's brand spend delta) > \$200
  - is_nea              = from FCT_BRAND_SESSIONS

Include all brands where abs(spend_delta) > \$100 (for totals line).
Sort by spend_delta ASC (most negative first).

For brands where abs(spend_delta) > \$500:
  - Get top publisher breakdown (which publishers drove most of the change).
  - Note page-type concentration if > 50% of delta is on a single page type.

Display rules:
  Spend DOWN: list brands with spend_delta <= -\$500
  Spend UP:   list brands with spend_delta > +\$100

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — Deliver Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DELIVERY 1 — Slack channel C0AV8GH3EQ5 (#supply-health-weekly)
Use this EXACT format:

:bar_chart: _WEEKLY PUBLISHER HEALTH REPORT — ${TODAY}_
_Rolling window: ${CURRENT_START}–${CURRENT_END} vs ${PRIOR_START}–${PRIOR_END}_

_TL;DR:_ [2-4 sentence narrative covering: (1) which page types moved and by how much,
(2) demand-side vs supply-side cause, (3) top 2-3 advertiser spend drivers by dollar impact
with publisher count, (4) any bright spots. Be specific with dollar amounts.]

━━ RPL BY PAGE TYPE — ALL PUBS (excl. MB/GP) ━━

| Page Type | Prior RPL | Current RPL | WoW Δ |
|-----------|-----------|-------------|-------|
| TYP       | \$X.XXXX   | \$X.XXXX     | X%    |
| OSP       | \$X.XXXX   | \$X.XXXX     | X%    |
| OTP       | \$X.XXXX   | \$X.XXXX     | X%    |
| Support   | \$X.XXXX   | \$X.XXXX     | X%    |

_[DFL direction summary — e.g. 'DFLs up across all pages (+14.7% TYP) — confirmed demand-side'
or 'DFLs down (TYP −18%) — supply-side contraction']_

━━ RPL BY PAGE TYPE — GOPUFF / BEVMO ━━

| Segment | Page Type | Prior RPL | Current RPL | WoW Δ |
|---------|-----------|-----------|-------------|-------|
| Gopuff  | TYP       | \$X.XXXX   | \$X.XXXX     | X%    |
| ...     | ...       | ...       | ...         | ...   |

━━ RPL BY ACTION TYPE — MINDBODY ━━

| Action Group | Prior RPL | Current RPL | WoW Δ |
|---|---|---|---|
| Booking  | \$X.XXXX | \$X.XXXX | X% |
| Purchase | \$X.XXXX | \$X.XXXX | X% |

_Moroccanoil CPM included. [One line: booking/purchase volume note — e.g.
'Booking volume flat ~1.09M — decline is spend-side (\$24.0k prior vs \$22.6k current).']_

━━ :warning: NETWORK-WIDE ADVERTISER SIGNALS ━━

_Spend DOWN:_
• [Brand] [NEA] — _−\$X,XXX_ across N publishers · [concentration note if applicable]
[all brands with spend_delta <= -\$500, most negative first]

_Spend UP:_
• [Brand] [NEA] — _+\$X,XXX_ across N publishers · [context]
[all brands with spend_delta > +\$100, largest first]
[if none: 'No brands with net spend increase above \$100 threshold this week.']

_Total identified spend down: ~−\$X,XXX · Total identified spend up: ~+\$X,XXX · Net: ~−\$X,XXX_
*Sent using* <@U0AGG5F5HEY>

FORMATTING RULES for Slack:
- [NEA] label only when is_nea = true
- 'went to zero' when current_spend = 0
- publisher_count = distinct publishers where that brand's spend delta exceeded \$200 in the same direction
- page type concentration note when > 50% of brand's total spend delta is on one page type
- do NOT include an RPM Summary section
- do NOT include a full per-publisher account breakdown

DELIVERY 2 — HTML email
  To:      mlevy@disconetwork.com
  Subject: 📊 Weekly Publisher Health Report — ${TODAY}
  Body:    same content as Slack but formatted as clean HTML:
    - Section headers as <h2> tags
    - RPL tables as <table> elements with border='1' cellpadding='6'
    - Inline color styling: decline rows background-color #fff0f0, increase rows #f0fff4
    - Keep emoji flags
    - Include the per-publisher breakdown for large brands (abs delta > \$500)
      as an additional section not present in Slack
"
