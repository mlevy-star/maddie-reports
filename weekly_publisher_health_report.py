#!/usr/bin/env python3
"""
Daily Publisher Health Report Runner
Sends to: Slack #supply-health-weekly (C0AV8GH3EQ5) + email mlevy@disconetwork.com
Schedule: Daily at 9:00 AM (see cron.txt)

Report sections (in order):
  1. Network-wide signals
  2. RPL by page type — All Pubs (excl. MB/GP/BevMo)
  3. RPL by page type — Gopuff / BevMo
  4. RPL by action type — Mindbody
  5. OTP DFL WoW — All Publishers
  6. BOTTOM LINE

Formatting requirements:
  - After each RPL/DFL table, include 1–2 italic sentences naming the top advertiser drivers
    and their dollar contribution (e.g. "Booking group: mostly endemic — Cuts Clothing (−$5.2K)
    + Kenny Flowers (−$2.6K) = ~54% of the decline.")
  - End every report with a BOTTOM LINE block containing:
      • A plain-English root-cause summary (what is actually happening, not a list of symptoms)
      • 2–3 recommended actions with emoji indicators (🔍 investigate, 📋 follow-up, 📈 monitor)
      • Links to the Hex threads used to pull the data

The Publisher Alerts / RPM section and the full account breakdown are intentionally excluded.
"""

import datetime

# Report configuration
REPORT_CONFIG = {
    "slack_channel_id": "C0AV8GH3EQ5",  # #supply-health-weekly
    "email_to": "mlevy@disconetwork.com",
    "email_subject_template": "📊 Weekly Publisher Health Report — {date}",

    # Hex project (workspace: 01975719-79d0-711b-a61c-0d574da7873a)
    "hex_supply_performance_url": "https://app.hex.tech/01975719-79d0-711b-a61c-0d574da7873a/app/Supply-Performance-032glc8YVtMzC5RWVsOqqQ/latest",

    # Health flag thresholds (applied to RPL WoW Δ)
    "thresholds": {
        "critical": -0.20,    # RPL drop > 20%
        "at_risk": -0.10,     # RPL drop 10–20%
        "increase": 0.10,     # RPL gain > 10%
        # else: HEALTHY (±10%)
    },

    # Page type mappings (raw DB value -> display label); MODAL excluded
    "page_types": {
        "THANK_YOU": "TYP",
        "ORDER_STATUS": "OSP",
        "ORDER_TRACKING": "OTP",
        "SUPPORT_CENTER": "Support",
    },
}

# Publisher segments
SEGMENTS = {
    "all_pubs": {
        "description": "All publishers excluding Mindbody, Gopuff, BevMo",
        "exclude": ["Mindbody", "Gopuff", "BevMo"],
        "source": "FCT_SESSIONS + FCT_BRAND_SESSIONS",
    },
    "gopuff_bevmo": {
        "description": "Gopuff and BevMo segment",
        "include": ["Gopuff", "BevMo"],
        "source": "FCT_SESSIONS + FCT_BRAND_SESSIONS",
        "note": "Only TYP and OSP pages observed; no OTP or Support traffic",
    },
    "mindbody": {
        "description": "Mindbody — custom pipeline",
        "include": ["Mindbody"],
        "source": "reporting.event + reporting.combined_cpc_cpa_ad_spend_revenue",
        "pipeline": {
            "deduplication": "lag() over order_id ordered by event_created_at — first event per order only",
            "moroccanoil_cpm": "impressions × $0.10 from widget_viewable_threshold_brand_display events",
            "action_groups": {
                # Pre-purchase confirmation pages
                "BOOKING GROUP": ["booking", "upcoming_booking"],
                # Completed transactions
                "PURCHASE GROUP": ["purchase", "booking_and_purchase"],
            },
            "transaction_type_field": "CUSTOM_METADATA:transactionType",
            "session_events": "widget_load (deduplicated by order_id)",
            "spend_events": [
                "widget_brand_click",
                "widget_viewable_threshold_brand_display",
                "widget_brand_display",
            ],
        },
    },
}

# RPL formula (Supply Performance)
RPL_FORMULA = "sum(billable_amount) / sum(sessions_with_widget_display)"

# DFL section — OTP only, all publishers (excl. Mindbody which uses a different event schema)
# Source: FCT_SESSIONS only (do NOT join FCT_BRAND_SESSIONS — fans out row counts)
# Metric: sum(sessions_with_widget_display) per publisher per window
# Compare current 7-day window vs prior 7-day window; report % change WoW
# Sort by abs(dfl_delta) descending; flag with same thresholds as RPL
DFL_SECTION = {
    "page_type": "ORDER_TRACKING",   # OTP only
    "source": "FCT_SESSIONS",
    "hex_narvar_report_url": "https://app.hex.tech/01975719-79d0-711b-a61c-0d574da7873a/app/EXT-Narvar-Reporting-031SR1hJTJuTVbRq5TSxa8/latest",
    "metric": "sum(sessions_with_widget_display)",
    "segments": "all publishers with OTP traffic (excl. Mindbody)",
    "sort": "abs(dfl_delta) DESC",
    "note": "Narvar report is the preferred source for OTP DFL data; fall back to FCT_SESSIONS if unavailable",
}

# Advertiser attribution
# Always GROUP BY brand_display_context (Hero vs. Multiple) to avoid double-counting spend.
# Compute session counts from FCT_SESSIONS alone — joining FCT_BRAND_SESSIONS fans out rows.
# CPA conversion counts unreliable since Dec 2025; use billable_amount for all attribution.
ATTRIBUTION = {
    "join": "FCT_SESSIONS s JOIN FCT_BRAND_SESSIONS bs ON s.session_id = bs.session_id",
    "group_by": ["publisher_name", "page_type", "brand_name", "is_nea", "brand_display_context"],
    "order_by": "abs(spend_delta) DESC",
    "limit_per_group": 5,
    "cross_publisher_signal_threshold": 3,  # Flag if top driver across >= 3 publishers
}


def get_report_window(as_of: datetime.date = None):
    """Return (current_start, current_end, prior_start, prior_end) as rolling 7-day windows.

    current  = [as_of - 7, as_of - 1]  (last 7 days through yesterday)
    prior    = [as_of - 14, as_of - 8] (7 days before that)
    """
    if as_of is None:
        as_of = datetime.date.today()
    current_end = as_of - datetime.timedelta(days=1)
    current_start = as_of - datetime.timedelta(days=7)
    prior_end = as_of - datetime.timedelta(days=8)
    prior_start = as_of - datetime.timedelta(days=14)
    return current_start, current_end, prior_start, prior_end


if __name__ == "__main__":
    current_start, current_end, prior_start, prior_end = get_report_window()
    print(f"Report window: {current_start} – {current_end} vs. {prior_start} – {prior_end}")
    print("To run: invoke via Claude Code with Hex MCP + Slack MCP + Gmail MCP")
    print(f"Slack channel: {REPORT_CONFIG['slack_channel_id']}")
    print(f"Email: {REPORT_CONFIG['email_to']}")
