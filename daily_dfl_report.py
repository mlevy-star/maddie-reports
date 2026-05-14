# Daily DFL / Ad Opportunity Report — Claude Code Routine

**Routine name:** Daily DFL Report
**Schedule:** Daily (Mon–Sun) at 9:00 AM (your local timezone)
**Connectors required:** Hex, Slack
**Slack channel:** #supply-health-weekly (ID: C0AV8GH3EQ5)

---

## Setup Instructions

1. Go to **[claude.ai/code](https://claude.ai/code)** → click **Routines** → **New Routine**
2. Set schedule: **Daily → Mon–Sun → 9:00 AM**
3. Enable connectors: **Hex** + **Slack**
4. Paste everything inside the code block below into the Routine prompt field and save

---

## Routine Prompt

Run the Daily DFL / Ad Opportunity Report and deliver it to Slack channel C0AV8GH3EQ5.

DATE WINDOWS (always rolling, never calendar):
  current window = today minus 7 days through yesterday
  prior window   = today minus 14 days through today minus 8 days

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — Query Hex
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use the Hex Threads agent against the Supply Performance project
(projectId: 019ce306-f016-700c-aed9-a9ba95d827c2).

Source: FCT_SESSIONS only. Do NOT join FCT_BRAND_SESSIONS (it fans out session counts).
Include ALL publishers — Mindbody, Gopuff, BevMo, everyone. Exclude MODAL page type.

For each publisher + page_type combination compute:
  - prior_dfl_sessions   = sessions_with_widget_display count in prior window
  - current_dfl_sessions = sessions_with_widget_display count in current window
  - dfl_wow_pct          = (current - prior) / nullif(prior, 0)
  - prior_total_sessions   = total widget-load sessions in prior window
  - current_total_sessions = total widget-load sessions in current window
  - prior_fill_rate   = prior_dfl_sessions / prior_total_sessions
  - current_fill_rate = current_dfl_sessions / current_total_sessions
  - fill_rate_delta_ppts = current_fill_rate - prior_fill_rate

Filter noise: only include rows where prior_dfl_sessions > 500 OR current_dfl_sessions > 500.

Then compute TWO rollups from the same data:

ROLLUP A — Page-type aggregate (network-wide, all publishers summed):
  For each of TYP (THANK_YOU), OSP (ORDER_STATUS), OTP (ORDER_TRACKING), Support (SUPPORT_CENTER):
    - sum(prior_dfl_sessions), sum(current_dfl_sessions)
    - dfl_wow_pct
    - fill_rate = sum(dfl_sessions) / sum(total_sessions)
    - fill_rate_delta_ppts
  Sort order: TYP, OSP, OTP, Support.

ROLLUP B — Major shifts per publisher × page_type:
  Flag IS_MAJOR_DFL_SHIFT = abs(dfl_wow_pct) > 0.20
  Separate flagged rows into:
    - Ramps: dfl_wow_pct > +20%, sorted largest first
    - Drops: dfl_wow_pct < −20%, sorted most negative first
  If no rows flagged, write "No major DFL shifts (>20%) this week."
  Also note any publisher where current_dfl_sessions = 0 ("went to zero")
  and any fill rate shift > 5 ppts.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — Send to Slack
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Send one message to Slack channel C0AV8GH3EQ5 using this exact format:

:bar_chart: _DAILY DFL REPORT — [Date]_
_Rolling window: [current_start]–[current_end] vs [prior_start]–[prior_end]_


━━ DFLs BY PAGE TYPE — ALL PUBLISHERS ━━

| Page Type | Prior DFLs | Current DFLs | WoW Δ | Fill Rate Δ |
|-----------|-----------|-------------|-------|-------------|
| TYP       | X,XXX,XXX  | X,XXX,XXX   | X%    | X.X ppts    |
| OSP       | X,XXX,XXX  | X,XXX,XXX   | X%    | X.X ppts    |
| OTP       | X,XXX,XXX  | X,XXX,XXX   | X%    | X.X ppts    |
| Support   | XX,XXX     | XX,XXX      | X%    | X.X ppts    |

_[One line: net network DFLs total prior vs current and overall %; note if fill rate
 is flat (volume story) or shifting (auction/fill story).]_


━━ :warning: MAJOR SHIFTS (publisher × page type, abs WoW > 20%) ━━

_Ramps:_
• [Publisher] [Page Type] — prior: X,XXX → current: X,XXX (+X%) · fill rate: X.X ppts
[sorted largest first; if none write "None above 20% threshold."]

_Drops:_
• [Publisher] [Page Type] — prior: X,XXX → current: X,XXX (−X%) · fill rate: X.X ppts
[sorted most negative first; add "went to zero" if current_dfl = 0; if none write "None above 20% threshold."]

_Fill rate shifts > 5 ppts: [list any, or "None."]_

*Sent using* <@U0AGG5F5HEY>
