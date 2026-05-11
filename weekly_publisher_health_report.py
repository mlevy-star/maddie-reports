Run the Weekly Publisher Health Report and deliver it to Slack channel C0AV8GH3EQ5.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — Pull data from Hex
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use the Hex Threads agent to run the following queries against the Supply Performance project.

DATE WINDOWS (always rolling, never calendar week):
  current window = today minus 7 days through yesterday
  prior window   = today minus 14 days through today minus 8 days

RPL = sum(billable_amount) / sum(sessions_with_widget_display)

--- SECTION A: All Publishers (excl. Mindbody, Gopuff, BevMo) ---
Tables: FCT_SESSIONS + FCT_BRAND_SESSIONS
Page types (exclude MODAL):
  TYP = THANK_YOU, OSP = ORDER_STATUS, OTP = ORDER_TRACKING, Support = SUPPORT_CENTER

For each page type compute:
  - prior_rpl, current_rpl
  - wow_delta = (current_rpl - prior_rpl) / nullif(prior_rpl, 0)
  - DFL direction = is sessions_with_widget_display up or down WoW?
    (compute from FCT_SESSIONS alone — do NOT join FCT_BRAND_SESSIONS for DFL counts)

--- SECTION B: Gopuff / BevMo ---
Same tables and logic as Section A, filtered to Gopuff and BevMo publishers only.

--- SECTION C: Mindbody ---
Tables: reporting.event + reporting.combined_cpc_cpa_ad_spend_revenue
Special rules:
  - Ad-ops dedup: use lag() windowing to count only first-event sessions per order
  - Moroccanoil CPM: billable_amount += impressions * $0.10
  - Group into TWO buckets:
      Booking  = Booking + Upcoming Booking
      Purchase = Purchase + Booking & Purchase
Compute prior_rpl, current_rpl, wow_delta for each bucket.
Note whether the change is spend-side or volume-side (compare ad_ops session count WoW).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — Network-Wide Advertiser Signals
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use Hex Threads to query FCT_BRAND_SESSIONS joined to FCT_SESSIONS on session_id.
Exclude Mindbody. Always include brand_display_context in GROUP BY (prevents double-counting Hero vs. Multiple placements).

For each brand_name compute:
  - total_prior_spend, total_current_spend across all publishers and page types
  - spend_delta = total_current_spend - total_prior_spend
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

Send one message to Slack channel C0AV8GH3EQ5 using this exact format:

:bar_chart: _WEEKLY PUBLISHER HEALTH REPORT — [Date]_
_Rolling window: [current_start]–[current_end] vs [prior_start]–[prior_end]_



_TL;DR:_ [2-4 sentences covering: which page types moved and by how much; whether demand-side (DFLs flat/up, spend fell) or supply-side (DFLs fell); top 2-3 advertiser spend drivers by dollar amount with publisher count; any bright spots. Be specific with dollar figures.]



━━ RPL BY PAGE TYPE — ALL PUBS (excl. MB/GP) ━━

| Page Type | Prior RPL | Current RPL | WoW Δ |
|-----------|-----------|-------------|-------|
| TYP       | $X.XXXX   | $X.XXXX     | X%    |
| OSP       | $X.XXXX   | $X.XXXX     | X%    |
| OTP       | $X.XXXX   | $X.XXXX     | X%    |
| Support   | $X.XXXX   | $X.XXXX     | X%    |

_[One line DFL summary — e.g. "DFLs up across all pages (+14.7% TYP) — confirmed demand-side" or "DFLs down (TYP −18%) — supply-side contraction"]_


━━ RPL BY PAGE TYPE — GOPUFF / BEVMO ━━

| Segment | Page Type | Prior RPL | Current RPL | WoW Δ |
|---------|-----------|-----------|-------------|-------|
| Gopuff  | TYP       | $X.XXXX   | $X.XXXX     | X%    |
| BevMo   | ...       | ...       | ...         | ...   |


━━ RPL BY ACTION TYPE — MINDBODY ━━

| Action Group | Prior RPL | Current RPL | WoW Δ |
|---|---|---|---|
| Booking  | $X.XXXX | $X.XXXX | X% |
| Purchase | $X.XXXX | $X.XXXX | X% |

_Moroccanoil CPM included. [One line on booking/purchase volume — e.g. "Booking volume flat ~1.09M — decline is spend-side ($24.0k prior vs $22.6k current)."]_


━━ :warning: NETWORK-WIDE ADVERTISER SIGNALS ━━

_Spend DOWN:_
• [Brand] [NEA] — _−$X,XXX_ across N publishers · [concentration note if applicable]
[all brands with spend_delta ≤ −$500, most negative first; add "· went to zero" if current_spend = 0]

_Spend UP:_
• [Brand] [NEA] — _+$X,XXX_ across N publishers · [context]
[all brands with spend_delta > +$100, largest first; if none: "No brands above $100 threshold this week."]

_Total identified spend down: ~−$X,XXX · Total identified spend up: ~+$X,XXX · Net: ~−$X,XXX_
*Sent using* <@U0AGG5F5HEY>
