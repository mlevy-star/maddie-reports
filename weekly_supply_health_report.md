# Weekly Supply Health Report — Claude Code Routine

**Routine name:** Weekly Supply Health Report
**Schedule:** Weekly → Monday → 10:00 AM ET
**Connectors required:** Hex, Slack
**Slack channel:** C0B3SPRNT9B

---

## Setup Instructions (claude.ai/code)

1. Go to **[claude.ai/code](https://claude.ai/code)** → click **Routines** → **New Routine**
2. Set schedule: **Weekly → Monday → 10:00 AM**
3. Enable connectors: **Hex** + **Slack**
4. Paste everything inside the prompt block below into the Routine prompt field and save

---

## Routine Prompt

Run the Weekly Publisher Health Report and deliver it to Slack channel C0B3SPRNT9B.

Today's date is {{TODAY}}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — Pull data from Hex
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use the Hex Threads agent to run the following queries against the Supply Performance project
(projectId: 019ce306-f016-700c-aed9-a9ba95d827c2).

DATE WINDOWS (always rolling, never calendar week):
  current window = today minus 7 days through yesterday
  prior window   = today minus 14 days through today minus 8 days
  30d window     = today minus 30 days through yesterday
                   (rolling 30-day baseline that includes both the current and prior 7-day windows)

RPL = sum(billable_amount) / sum(sessions_with_widget_display)

--- SECTION A: All Publishers (excl. Mindbody, Gopuff, BevMo) ---
Tables: FCT_SESSIONS + FCT_BRAND_SESSIONS
Page types (exclude MODAL):
  TYP = THANK_YOU, OSP = ORDER_STATUS, OTP = ORDER_TRACKING, Support = SUPPORT_CENTER

For each page type compute:
  - 30d_rpl     = RPL over the 30d window
  - prior_rpl   = RPL over the prior 7-day window
  - current_rpl = RPL over the current 7-day window
  - wow_delta   = (current_rpl - prior_rpl) / nullif(prior_rpl, 0)
  - vs_30d      = (current_rpl - 30d_rpl) / nullif(30d_rpl, 0)
  - prior_dfl   = sum(sessions_with_widget_display) over the prior 7-day window
  - current_dfl = sum(sessions_with_widget_display) over the current 7-day window
  - dfl_wow     = (current_dfl - prior_dfl) / nullif(prior_dfl, 0)
  DFL counts: compute from FCT_SESSIONS alone — do NOT join FCT_BRAND_SESSIONS (fan-out risk).

--- SECTION B: Gopuff / BevMo ---
Same tables and logic as Section A, filtered to Gopuff and BevMo publishers only.
Compute 30d_rpl, prior_rpl, current_rpl, wow_delta, vs_30d for each publisher × page type.
Also compute prior_dfl, current_dfl, dfl_wow per publisher × page type (from FCT_SESSIONS only).

--- SECTION C: Mindbody ---
Tables: reporting.event + reporting.combined_cpc_cpa_ad_spend_revenue
Special rules:
  - Ad-ops dedup: use lag() windowing to count only first-event sessions per order
  - Moroccanoil CPM: billable_amount += impressions * $0.10
  - Group into TWO buckets:
      Booking  = Booking + Upcoming Booking
      Purchase = Purchase + Booking & Purchase
Compute 30d_rpl, prior_rpl, current_rpl, wow_delta, vs_30d for each bucket.
Also report ad_ops session count (prior vs current) per bucket — this is the Mindbody DFL equivalent.
Compute dfl_wow = (current_sessions - prior_sessions) / nullif(prior_sessions, 0) per bucket.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — Network-Wide Advertiser Signals
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use Hex Threads to query FCT_BRAND_SESSIONS joined to FCT_SESSIONS on session_id.
Exclude Mindbody. Always include brand_display_context in GROUP BY (prevents double-counting).

For each brand_name compute:
  - total_prior_spend, total_current_spend across all publishers and page types
  - spend_delta = total_current_spend - total_prior_spend
  - total_30d_avg_weekly_spend = sum(billable_amount over 30d window) / (30/7)
    (annualized weekly run-rate from the 30d window, for trend context)
  - publisher_count = distinct publishers where |that brand's spend delta| > $200
  - is_nea flag

Totals: include all brands where abs(spend_delta) > $100.
Display:
  Spend DOWN = brands with spend_delta ≤ −$500, sorted most negative first
  Spend UP   = brands with spend_delta > +$100, sorted largest first

For brands where abs(spend_delta) > $500, note which publishers drove the change
and flag if >50% of the delta is concentrated on a single page type.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — Send to Slack
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Send one message to Slack channel C0B3SPRNT9B using this exact format:

:bar_chart: _WEEKLY PUBLISHER HEALTH REPORT — [Date]_
_Rolling window: [current_start]–[current_end] vs [prior_start]–[prior_end] · 30d baseline: [30d_start]–[30d_end]_



_TL;DR:_ [2-4 sentences: which page types moved WoW and by how much; whether demand-side
(DFLs flat/up, spend fell) or supply-side (DFLs fell); whether current week RPL is above or
below the 30d average; top 2-3 advertiser spend drivers by dollar amount with publisher count;
any bright spots. Be specific with dollar figures.]



━━ RPL BY PAGE TYPE — ALL PUBS (excl. MB/GP) ━━

| Page Type | 30d Avg RPL | Prior RPL | Current RPL | WoW Δ | vs 30d Avg |
|-----------|-------------|-----------|-------------|-------|------------|
| TYP       | $X.XXXX     | $X.XXXX   | $X.XXXX     | X%    | X%         |
| OSP       | $X.XXXX     | $X.XXXX   | $X.XXXX     | X%    | X%         |
| OTP       | $X.XXXX     | $X.XXXX   | $X.XXXX     | X%    | X%         |
| Support   | $X.XXXX     | $X.XXXX   | $X.XXXX     | X%    | X%         |

_[One line DFL summary — e.g. "DFLs up across all pages (TYP +14.7% WoW) — confirmed demand-side"
or "DFLs down (TYP −18% WoW) — supply-side contraction. See DFL table below for full detail."]_


━━ RPL BY PAGE TYPE — GOPUFF / BEVMO ━━

| Segment | Page Type | 30d Avg RPL | Prior RPL | Current RPL | WoW Δ | vs 30d Avg |
|---------|-----------|-------------|-----------|-------------|-------|------------|
| Gopuff  | TYP       | $X.XXXX     | $X.XXXX   | $X.XXXX     | X%    | X%         |
| BevMo   | TYP       | $X.XXXX     | $X.XXXX   | $X.XXXX     | X%    | X%         |
| BevMo   | OSP       | $X.XXXX     | $X.XXXX   | $X.XXXX     | X%    | X%         |
| ...     | ...       | ...         | ...       | ...         | ...   | ...        |


━━ RPL BY ACTION TYPE — MINDBODY ━━

| Action Group | 30d Avg RPL | Prior RPL | Current RPL | WoW Δ | vs 30d Avg |
|---|---|---|---|---|---|
| Booking  | $X.XXXX | $X.XXXX | $X.XXXX | X% | X% |
| Purchase | $X.XXXX | $X.XXXX | $X.XXXX | X% | X% |

_Moroccanoil CPM included. [One line on booking/purchase volume WoW and vs 30d baseline —
e.g. "Booking volume +2% WoW but −5% vs 30d avg (~1.12M) — trend is softening spend-side."]_


━━ DFL (SESSIONS WITH WIDGET DISPLAY) — WoW ━━

_All Pubs (excl. MB/GP):_

| Page Type | Prior DFLs | Current DFLs | WoW Δ |
|-----------|------------|--------------|-------|
| TYP       | X,XXX,XXX  | X,XXX,XXX    | X%    |
| OSP       | X,XXX,XXX  | X,XXX,XXX    | X%    |
| OTP       | X,XXX,XXX  | X,XXX,XXX    | X%    |
| Support   | X,XXX,XXX  | X,XXX,XXX    | X%    |

_Gopuff / BevMo:_

| Segment | Page Type | Prior DFLs | Current DFLs | WoW Δ |
|---------|-----------|------------|--------------|-------|
| Gopuff  | TYP       | X,XXX,XXX  | X,XXX,XXX    | X%    |
| BevMo   | TYP       | X,XXX,XXX  | X,XXX,XXX    | X%    |
| BevMo   | OSP       | X,XXX,XXX  | X,XXX,XXX    | X%    |
| ...     | ...       | ...        | ...          | ...   |

_Mindbody (ad-ops deduped sessions):_

| Action Group | Prior Sessions | Current Sessions | WoW Δ |
|---|---|---|---|
| Booking  | X,XXX,XXX | X,XXX,XXX | X% |
| Purchase | X,XXX,XXX | X,XXX,XXX | X% |


━━ :warning: NETWORK-WIDE ADVERTISER SIGNALS ━━

_Spend DOWN:_
• [Brand] [NEA] — _−$X,XXX_ across N publishers · [concentration note if applicable]
[all brands with spend_delta ≤ −$500, most negative first; add "· went to zero" if current_spend = 0]

_Spend UP:_
• [Brand] [NEA] — _+$X,XXX_ across N publishers · [context]
[all brands with spend_delta > +$100, largest first; if none: "No brands above $100 threshold this week."]

_Total identified spend down: ~−$X,XXX · Total identified spend up: ~+$X,XXX · Net: ~−$X,XXX_
*Sent using* <@U0AGG5F5HEY>
