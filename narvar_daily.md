You are running the Narvar Order Tracking Page (OTP) daily publisher health
check. Today's date is {{TODAY}}. Complete all steps silently — do not ask
clarifying questions. Post results to Slack when done.

### Step 1 — Pull DFL data from Snowflake

Use Hex to run this SQL against ANALYTICS.PROD (publisher_name is on FCT_SESSIONS directly):

WITH daily AS (
    SELECT publisher_name, dt, COUNT(DISTINCT session_id) AS dfls
    FROM ANALYTICS.PROD.FCT_SESSIONS
    WHERE page_type = 'OTP'
      AND dt BETWEEN DATEADD('day', -13, CURRENT_DATE - 1) AND CURRENT_DATE - 1
    GROUP BY 1, 2
),
current_week AS (
    SELECT publisher_name, SUM(dfls) AS dfls_curr
    FROM daily
    WHERE dt BETWEEN DATEADD('day', -6, CURRENT_DATE - 1) AND CURRENT_DATE - 1
    GROUP BY 1
),
prior_week AS (
    SELECT publisher_name, SUM(dfls) AS dfls_prior
    FROM daily
    WHERE dt BETWEEN DATEADD('day', -13, CURRENT_DATE - 1)
                 AND DATEADD('day', -7, CURRENT_DATE - 1)
    GROUP BY 1
)
SELECT
    c.publisher_name,
    p.dfls_prior,
    c.dfls_curr,
    c.dfls_curr - p.dfls_prior AS abs_change,
    ROUND((c.dfls_curr - p.dfls_prior) / NULLIF(p.dfls_prior, 0) * 100, 1) AS pct_change
FROM current_week c
JOIN prior_week p ON c.publisher_name = p.publisher_name
WHERE p.dfls_prior >= 1000
ORDER BY pct_change ASC;

### Step 2 — Pull RPL data from Snowflake via Hex

WITH sessions AS (
    SELECT publisher_name, dt,
           COUNT(DISTINCT session_id) AS dfls,
           SUM(total_billable_amount) AS revenue
    FROM ANALYTICS.PROD.FCT_SESSIONS
    WHERE page_type = 'OTP'
      AND dt BETWEEN DATEADD('day', -13, CURRENT_DATE - 1) AND CURRENT_DATE - 1
    GROUP BY 1, 2
),
current_week AS (
    SELECT publisher_name, SUM(dfls) AS dfls_curr, SUM(revenue) AS rev_curr
    FROM sessions
    WHERE dt BETWEEN DATEADD('day', -6, CURRENT_DATE - 1) AND CURRENT_DATE - 1
    GROUP BY 1
),
prior_week AS (
    SELECT publisher_name, SUM(dfls) AS dfls_prior, SUM(revenue) AS rev_prior
    FROM sessions
    WHERE dt BETWEEN DATEADD('day', -13, CURRENT_DATE - 1)
                 AND DATEADD('day', -7, CURRENT_DATE - 1)
    GROUP BY 1
)
SELECT
    c.publisher_name,
    ROUND(p.rev_prior / NULLIF(p.dfls_prior, 0), 6) AS rpl_prior,
    ROUND(c.rev_curr  / NULLIF(c.dfls_curr,  0), 6) AS rpl_curr,
    ROUND(
        ((c.rev_curr / NULLIF(c.dfls_curr, 0))
       - (p.rev_prior / NULLIF(p.dfls_prior, 0)))
      / NULLIF(p.rev_prior / NULLIF(p.dfls_prior, 0), 0) * 100,
    1) AS rpl_pct_change
FROM current_week c
JOIN prior_week p ON c.publisher_name = p.publisher_name
ORDER BY rpl_pct_change ASC;

### Step 3 — Pull top 5 advertisers for all flagged publishers (both weeks)

A publisher is flagged if: DFL WoW decline > 10% OR RPL WoW decline > 15%.

Run via Hex, substituting flagged publisher names:

WITH ranked AS (
    SELECT
        s.publisher_name,
        b.brand_name,
        CASE
            WHEN s.dt BETWEEN DATEADD('day', -6, CURRENT_DATE - 1) AND CURRENT_DATE - 1
            THEN 'curr' ELSE 'prior'
        END AS wk,
        SUM(bs.billable_amount) AS revenue,
        ROW_NUMBER() OVER (
            PARTITION BY s.publisher_name,
                CASE WHEN s.dt BETWEEN DATEADD('day', -6, CURRENT_DATE - 1) AND CURRENT_DATE - 1
                THEN 'curr' ELSE 'prior' END
            ORDER BY SUM(bs.billable_amount) DESC
        ) AS rnk
    FROM ANALYTICS.PROD.FCT_SESSIONS s
    JOIN ANALYTICS.PROD.FCT_BRAND_SESSIONS bs ON s.session_id = bs.session_id
    JOIN ANALYTICS.PROD.DIM_BRANDS b ON bs.brand_id = b.brand_id
    WHERE s.page_type = 'OTP'
      AND s.dt BETWEEN DATEADD('day', -13, CURRENT_DATE - 1) AND CURRENT_DATE - 1
      AND s.publisher_name IN (/* FLAGGED_PUBLISHERS */)
    GROUP BY 1, 2, 3
)
SELECT publisher_name, wk, brand_name, ROUND(revenue, 2) AS revenue, rnk
FROM ranked
WHERE rnk <= 5
ORDER BY publisher_name, wk DESC, rnk;

### Step 4 — Apply flagging logic

DFL flag 🔴 — WoW decline > 10%
RPL flag ⚠️ — WoW decline > 15%
Double flag 🚨 — both DFL and RPL triggered (escalate same day)
All green ✅ — no flags

### Step 5 — Identify cross-publisher advertiser patterns for Network TLDR

Scan top-5 advertiser data across all flagged publishers and identify:
1. Any advertiser appearing as NEW across 2+ publishers — flag as possible network-level demand shift
2. Any advertiser whose revenue declined across 3+ publishers — flag as possible budget/bid change
Include as bullet points in Network TLDR. Omit section if no patterns exist.

### Step 6 — Post to Slack

Post TWO messages to channel ID C0B286G3SPK (#test-narvar-claude).

Message 1 — Main brief (post to channel):

*📊 Narvar OTP Daily Brief — {TODAY'S DATE}*
*Rolling 7d: {CURR_START}–{CURR_END} vs {PRIOR_START}–{PRIOR_END}*

*📌 Network TLDR*
• *{ADVERTISER}* {cross-publisher pattern}
[Omit if no patterns]

*🚨 Double Flags — escalate same day*
🔴 *{PUBLISHER}* | DFLs {DFL_PCT}% · RPL {RPL_PCT}% | {1-line callout}
[Omit if none]

*🔴 DFL Flags — >10% WoW decline*
▼ *{PUBLISHER}* | DFLs {DFL_PCT}% | {1-line note}
[Omit if none]

*⚠️ RPL Flags — revenue per load declining >15%*
↘ *{PUBLISHER}* | RPL {RPL_PCT}% · DFLs {DFL_PCT}% | {1-line note}
[Omit if none]

*📈 All Publishers*
Publisher | DFLs | DFL WoW | RPL | RPL WoW
{PUBLISHER} {FLAG} | {DFL_CURR} | {DFL_PCT}% | ${RPL_CURR} | {RPL_PCT}%
[Sorted: 🚨 first, then 🔴, then ⚠️, then ✅]

_<https://app.hex.tech/01975719-79d0-711b-a61c-0d574da7873a/app/EXT-Narvar-Reporting-031SR1hJTJuTVbRq5TSxa8/latest|📎 Full Narvar report> · Advertiser detail by publisher 👇_

Message 2 — Advertiser detail (post as thread reply to Message 1):

*🔍 Advertiser mix detail — flagged publishers*

*{PUBLISHER}* (RPL {RPL_PCT}%)
Prior: {ADV1} ${REV} · {ADV2} ${REV} · {ADV3} ${REV} · {ADV4} ${REV} · {ADV5} ${REV}
Curr: {ADV1} ${REV} ↓ · {ADV2} ${REV} ↑ · {ADV3} ${REV} 🆕

[↑ = revenue up WoW, ↓ = down WoW, 🆕 = new entry not in prior week top 5]

If NO flags, skip Message 2 and post only:

*📊 Narvar OTP Daily Brief — {TODAY'S DATE}*
✅ *All publishers healthy — no DFL or RPL flags today.*

*📈 All Publishers*
Publisher | DFLs | DFL WoW | RPL | RPL WoW
{PUBLISHER} ✅ | {DFL_CURR} | {DFL_PCT}% | ${RPL_CURR} | {RPL_PCT}%

_<https://app.hex.tech/01975719-79d0-711b-a61c-0d574da7873a/app/EXT-Narvar-Reporting-031SR1hJTJuTVbRq5TSxa8/latest|📎 Full Narvar report>_

## Flag Thresholds

DFL WoW decline: > 10%
RPL WoW decline: > 15%
Double flag: Both DFL + RPL triggered
Min publisher volume: >= 1,000 DFLs in prior week

## Notes

- Portfolio escalation: If two publishers with the same parent company (e.g. Victoria's Secret + Savage X Fenty) are both flagged, note explicitly and recommend escalating together.
- Advertiser watch: Low-CPM advertisers (e.g. Shipments Free) appearing as new top-5 entries across 2+ publishers signal network-level fill rate dilution — always call out in Network TLDR and flag to demand team.
