# Weekly Publisher Health Report — Claude Code Routine

**Routine name:** Weekly Publisher Health Report
**Schedule:** Daily (Mon–Sun) at 9:00 AM (your local timezone)
**Connectors required:** Hex, Slack, Gmail
**Slack channel:** #supply-health-weekly (ID: C0AV8GH3EQ5)
**Email recipient:** mlevy@disconetwork.com

---

## Setup Instructions

1. Go to **[claude.ai/code](https://claude.ai/code)** → click **Routines** → **New Routine**
2. Set schedule: **Daily → Mon–Sun → 9:00 AM**
3. Enable connectors: **Hex** + **Slack** + **Gmail**
4. Paste everything inside the code block below into the Routine prompt field and save

---

## Routine Prompt

Every Monday morning, run the Weekly Publisher Health Report.
Pull from three data sources, then deliver the report to BOTH Slack and email.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — RPM + Advertiser Attribution
Source: Publisher Alerts dashboard
URL: https://app.hex.tech/01975719-79d0-711b-a61c-0d574da7873a/app/Publisher-Alerts-0331EBOLFT7qulVc6c8qmh/latest
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each publisher account, extract:
- Last 7 days RPM vs the 7 days prior to that (rolling comparison, not calendar week)
- Which advertisers are driving any RPM increases or decreases
- Overall account health status

Always show RPM as dollar values: prior RPM ($X.XX) → current RPM ($X.XX), dollar change (−$X.XX), and % change as secondary context only.

Flag thresholds (based on % change, but always display dollar values):
🔴 CRITICAL = RPM drop >20%
🟡 AT RISK  = RPM drop 10–20%
📈 INCREASE = RPM up >10%
🟢 HEALTHY  = within ±10%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — RPL by Page Type, WoW (All Publishers)
Source: Supply Performance dashboard
URL: https://app.hex.tech/01975719-79d0-711b-a61c-0d574da7873a/app/Supply-Performance-032glc8YVtMzC5RWVsOqqQ/latest
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RPL = sum(billable_amount) / sum(sessions_with_widget_display), per page type.
Always compare the last 7 days (today minus 7 days through yesterday) vs the 7 days
prior to that (today minus 14 days through today minus 8 days) — regardless of what
day of the week the report runs.
Run THREE separate pipelines:

--- SECTION A: All Publishers (excl. Mindbody, Gopuff, Bevmo) ---
Source tables: FCT_SESSIONS + FCT_BRAND_SESSIONS
Page types to report (exclude MODAL):
  - TYP     (raw value: THANK_YOU)
  - OSP     (raw value: ORDER_STATUS)
  - OTP     (raw value: ORDER_TRACKING)
  - Support (raw value: SUPPORT_CENTER)

Compute WoW RPL delta per page type:
  (current_week_rpl - prior_week_rpl) / nullif(prior_week_rpl, 0)

Show network aggregate summary first, then individual publishers where
any page type moved >10% WoW.

--- SECTION B: Gopuff / Bevmo ---
Source tables: FCT_SESSIONS + FCT_BRAND_SESSIONS, filtered to Gopuff/Bevmo publishers
Same page type breakdown and WoW delta logic as Section A.

--- SECTION C: Mindbody ---
Source tables: reporting.event + reporting.combined_cpc_cpa_ad_spend_revenue
Use Mindbody's custom pipeline logic:
  - Ad-ops deduplication: use lag() windowing to count only first-event sessions per order
  - CPM spend for Moroccanoil: add impressions * $0.10 on top of standard billable_amount
  - Group action types into TWO buckets:

  BOOKING GROUP (combine Booking + Upcoming Booking):
    These share the same intent — pre-purchase confirmation pages.

  PURCHASE GROUP (combine Purchase + Booking & Purchase):
    These represent completed transactions.

Compute WoW RPL delta for each of the two Mindbody groups.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — DFL / Ad Opportunity Shifts (All Publishers)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Source: FCT_SESSIONS only (do NOT join FCT_BRAND_SESSIONS — it fans out session counts).
Include ALL publishers (Mindbody, Gopuff, BevMo, everyone). Exclude MODAL page type.
Use the same rolling date windows as STEP 2.

For each publisher + page_type combination, compute:
  - prior_dfl_sessions   = count of sessions where sessions_with_widget_display in prior window
  - current_dfl_sessions = count of sessions where sessions_with_widget_display in current window
  - dfl_wow_pct          = (current - prior) / nullif(prior, 0)
  - prior_total_sessions   = total widget-load sessions in prior window
  - current_total_sessions = total widget-load sessions in current window
  - prior_fill_rate   = prior_dfl_sessions / prior_total_sessions
  - current_fill_rate = current_dfl_sessions / current_total_sessions
  - fill_rate_delta_ppts = current_fill_rate - prior_fill_rate

Filter noise: only include rows where prior_dfl_sessions > 500 OR current_dfl_sessions > 500.

Flag rules:
  - IS_MAJOR_DFL_SHIFT   = abs(dfl_wow_pct) > 0.20
  - IS_FILL_RATE_SHIFT   = abs(fill_rate_delta_ppts) > 0.05

For the report, separate flagged rows into:
  - Ramps:  dfl_wow_pct > +20%, sorted largest first
  - Drops:  dfl_wow_pct < −20%, sorted most negative first
Only include IS_MAJOR_DFL_SHIFT rows in the report section.
If no rows are flagged, write: "No major DFL shifts (>20%) this week."

Also produce a publisher-level rollup (sum DFLs across page types) sorted by abs(dfl_wow_pct)
for context, but only surface it in the report if a publisher's rollup itself crosses ±20%.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — Advertiser Attribution for RPL Changes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For any publisher + page type where RPL moved >10% WoW, identify which
advertisers drove the spend change.

Join FCT_BRAND_SESSIONS to FCT_SESSIONS on session_id.
IMPORTANT: always include brand_display_context in GROUP BY to avoid
double-counting spend (Hero vs. Multiple placement is part of the grain).

Attribution query pattern:
  SELECT
    s.publisher_name,
    s.page_type,
    bs.brand_name,
    bs.is_nea,
    sum(CASE WHEN week = 'prior'   THEN bs.billable_amount END) as prior_spend,
    sum(CASE WHEN week = 'current' THEN bs.billable_amount END) as current_spend,
    (current_spend - prior_spend) as spend_delta,
    (spend_delta / total_page_rpl_delta) as pct_of_rpl_change
  FROM FCT_SESSIONS s
  JOIN FCT_BRAND_SESSIONS bs ON s.session_id = bs.session_id
  GROUP BY s.publisher_name, s.page_type, bs.brand_name, bs.is_nea, bs.brand_display_context
  ORDER BY abs(spend_delta) DESC

Surface top 5 advertisers by absolute spend delta per flagged publisher + page type.
Note whether each is NEA (is_nea = true) or standard.
Show each advertiser's % contribution to the total RPL change.

Also check: if any single advertiser appears as a top spend driver across 3+ publishers
in the same direction (increase or decrease), flag it as a network-wide signal.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — Deliver Report (Slack + Email)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Format the report as below, then deliver it in TWO ways:

DELIVERY 1 — Slack
  Send to channel: #supply-health-weekly (channel ID: C0AV8GH3EQ5)
  Use Slack markdown formatting (*bold*, newlines between sections)

DELIVERY 2 — Email via Gmail
  To: mlevy@disconetwork.com
  Subject: 📊 Weekly Publisher Health Report — [Date]
  Body: same content as Slack but formatted as clean HTML.
  - Section headers as <h2> tags
  - RPL and account breakdown tables as HTML <table> elements with borders
  - Inline color styling for flag rows:
      🔴 critical rows: background-color #fff0f0
      🟡 at-risk rows:  background-color #fffbe6
      📈 increase rows: background-color #f0fff4
  - Keep emoji flags for easy visual scanning

---

REPORT CONTENT FORMAT:

Always include a blank line between every section header and its content, and a blank line after each section before the next divider.

📊 WEEKLY PUBLISHER HEALTH REPORT — [Date]


━━ RPM SUMMARY ━━

RPM is a dollar value — always display as: Prior RPM → Current RPM (−$X.XX, −X%)

🔴 CRITICAL (RPM drop >20%):
  • [Publisher] | $X.XX → $X.XX (−$X.XX, −X%) | Top driver: [Advertiser] (−$X spend)

🟡 AT RISK (RPM drop 10–20%):
  • [Publisher] | $X.XX → $X.XX (−$X.XX, −X%) | Top driver: [Advertiser] (−$X spend)

📈 INCREASES:
  • [Publisher] | $X.XX → $X.XX (+$X.XX, +X%) | Top driver: [Advertiser] (+$X spend)

🟢 HEALTHY: [N] publishers stable (±10%)


---


━━ ⚠️ NETWORK-WIDE SIGNALS ━━

[Only include if any advertiser is a top driver across 3+ publishers in the same direction]
Example: "Rakuten: −$X spend across [N] publishers — driving RPL declines at
[Publisher A] (−X%), [Publisher B] (−X%), [Publisher C] (−X%)"

Omit this section entirely if there are no cross-publisher signals this week.


---


━━ RPL BY PAGE TYPE — ALL PUBS (excl. MB/GP) ━━

Network aggregate:

| Page Type | Prior RPL | Current RPL | WoW Δ  |
|-----------|-----------|-------------|--------|
| TYP       | $X.XX     | $X.XX       | +/−X%  |
| OSP       | $X.XX     | $X.XX       | +/−X%  |
| OTP       | $X.XX     | $X.XX       | +/−X%  |
| Support   | $X.XX     | $X.XX       | +/−X%  |

Publishers with any page type moving >10% WoW:

[Publisher Name] [🔴/🟡/📈]
| Page Type | Prior RPL | Current RPL | WoW Δ | Top Advertiser Driver          |
|-----------|-----------|-------------|-------|--------------------------------|
| TYP       | $X.XX     | $X.XX       | −X%   | [Advertiser]: −$X (X% of Δ)   |
| OSP       | $X.XX     | $X.XX       | −X%   | [Advertiser]: −$X (X% of Δ)   |


---


━━ RPL BY PAGE TYPE — GOPUFF / BEVMO ━━

[Same table format as All Pubs section above]


---


━━ RPL BY ACTION TYPE — MINDBODY ━━

Note: Moroccanoil CPM spend included (impressions × $0.10).

| Action Group | Prior RPL | Current RPL | WoW Δ  |
|--------------|-----------|-------------|--------|
| Booking      | $X.XX     | $X.XX       | +/−X%  |
| Purchase     | $X.XX     | $X.XX       | +/−X%  |


---


━━ 🔄 DFL / AD OPPORTUNITY SHIFTS — ALL PUBLISHERS ━━

Only show rows where abs(dfl_wow_pct) > 20%. If none, write: "No major DFL shifts (>20%) this week."

Ramps (DFL WoW > +20%), sorted largest first:
| Publisher | Page Type | Prior DFLs | Current DFLs | WoW Δ | Fill Rate Δ |
|-----------|-----------|-----------|-------------|-------|-------------|
| ...       | ...       | ...       | ...         | ...   | ...         |

Drops (DFL WoW < −20%), sorted most negative first:
| Publisher | Page Type | Prior DFLs | Current DFLs | WoW Δ | Fill Rate Δ |
|-----------|-----------|-----------|-------------|-------|-------------|
| ...       | ...       | ...       | ...         | ...   | ...         |

_[One line: call out any publisher that went to zero, any fill rate shift > 5 ppts, and whether
 the Footlocker/large-ramp context is publisher-side volume or fill improvement.]_

Note: fill rate here = DFL sessions / widget-load sessions within FCT_SESSIONS.
No fill rate shifts flagged = no ±5 ppt movers found.


---


━━ FULL ACCOUNT BREAKDOWN ━━

| Publisher | Prior RPM | Current RPM | RPM Δ$ | RPM Δ% | TYP RPL Δ | OSP RPL Δ | OTP RPL Δ | Support RPL Δ | Key Advertiser |

[All publishers sorted by largest negative RPM dollar change first]

---

## Data Notes

| Publisher Group        | Source Tables                                               | Notes                          |
|------------------------|-------------------------------------------------------------|--------------------------------|
| All Pubs (excl. MB/GP) | FCT_SESSIONS + FCT_BRAND_SESSIONS                           | Standard pipeline              |
| Gopuff / Bevmo         | FCT_SESSIONS + FCT_BRAND_SESSIONS (filtered)                | Same tables, publisher filter  |
| Mindbody               | reporting.event + reporting.combined_cpc_cpa_ad_spend_revenue | Custom dedup + CPM logic     |

**Mindbody action type groupings:**
- Booking group  = Booking + Upcoming Booking
- Purchase group = Purchase + Booking & Purchase

**Advertiser attribution gotchas:**
- Always GROUP BY brand_display_context (Hero vs. Multiple) — omitting it double-counts spend
- Compute DFLs from FCT_SESSIONS alone — joining to FCT_BRAND_SESSIONS fans out session counts
- CPA conversion counts unreliable since Dec 2025 — use billable_amount for all attribution
- is_nea = true flags NEA advertisers — surface as context in the report
