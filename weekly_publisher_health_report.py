#!/usr/bin/env python3
"""
Weekly Publisher Health Report Runner
Sends to: Slack #supply-health-weekly (C0AV8GH3EQ5) + email mlevy@disconetwork.com
Schedule: Every Monday morning (see cron.txt)
"""

import datetime

# Report configuration
REPORT_CONFIG = {
    "slack_channel_id": "C0AV8GH3EQ5",  # #supply-health-weekly
    "email_to": "mlevy@disconetwork.com",
    "email_subject_template": "📊 Weekly Publisher Health Report — {date}",

    # Hex app URLs
    "hex_publisher_alerts_url": "https://app.hex.tech/01975719-79d0-711b-a61c-0d574da7873a/app/Publisher-Alerts-0331EBOLFT7qulVc6c8qmh/latest",
    "hex_supply_performance_url": "https://app.hex.tech/01975719-79d0-711b-a61c-0d574da7873a/app/Supply-Performance-032glc8YVtMzC5RWVsOqqQ/latest",

    # Health flag thresholds
    "thresholds": {
        "critical": -0.20,    # RPM/RPL drop > 20%
        "at_risk": -0.10,     # RPM/RPL drop 10–20%
        "increase": 0.10,     # RPM/RPL gain > 10%
        # else: HEALTHY (±10%)
    },

    # Page type mappings (raw DB value -> display label)
    "page_types": {
        "THANK_YOU": "TYP",
        "ORDER_STATUS": "OSP",
        "ORDER_TRACKING": "OTP",
        "SUPPORT_CENTER": "Support",
        # MODAL excluded
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
                "BOOKING GROUP": ["booking"],
                "PURCHASE GROUP": ["purchase", "purchase_and_booking", "booking_and_purchase"],
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

# RPM formula (Publisher Alerts)
RPM_FORMULA = "sum(billable_amount) * 1000 / nullif(sum(brand_displays), 0)"
RPM_MIN_DISPLAYS = 100  # Minimum brand displays per week to include publisher

# RPL formula (Supply Performance)
RPL_FORMULA = "sum(billable_amount) / sum(sessions_with_widget_display)"

# Advertiser attribution
ATTRIBUTION = {
    "source": "FCT_BRAND_SESSIONS joined to FCT_SESSIONS on session_id",
    "group_by": ["publisher_name", "page_type", "brand_name", "is_nea", "brand_display_context"],
    "order_by": "abs(spend_delta) DESC",
    "limit_per_group": 5,
    "cross_publisher_signal_threshold": 3,  # Flag if top driver across >= 3 publishers
}


def get_report_window(as_of: datetime.date = None):
    """Return (current_start, current_end, prior_start, prior_end) as rolling 7-day windows.

    Current window: today-7 through yesterday
    Prior window:   today-14 through today-8
    Windows are day-of-week agnostic — valid whenever the report runs.
    """
    if as_of is None:
        as_of = datetime.date.today()
    current_end = as_of - datetime.timedelta(days=1)
    current_start = as_of - datetime.timedelta(days=7)
    prior_end = as_of - datetime.timedelta(days=8)
    prior_start = as_of - datetime.timedelta(days=14)
    return current_start, current_end, prior_start, prior_end


# Slack report format — match this structure exactly
# Reference: https://discotechnology.slack.com/archives/C0AV8GH3EQ5/p1778013284308369
SLACK_FORMAT = """
:bar_chart: _WEEKLY PUBLISHER HEALTH REPORT — {date}_
_Rolling window: {current_start}–{current_end} vs {prior_start}–{prior_end}_

_TL;DR:_ {narrative summary — RPL direction per page type, whether demand-side or supply-side,
top 2-3 advertiser spend drivers by dollar impact with publisher count, any bright spots}

━━ RPL BY PAGE TYPE — ALL PUBS (excl. MB/GP) ━━

{markdown table: Page Type | Prior RPL | Current RPL | WoW Δ}

_{one-line note on DFL direction and demand-side vs supply-side conclusion}_

━━ RPL BY PAGE TYPE — GOPUFF / BEVMO ━━

{markdown table: Segment | Page Type | Prior RPL | Current RPL | WoW Δ}

━━ RPL BY ACTION TYPE — MINDBODY ━━

{markdown table: Action Group | Prior RPL | Current RPL | WoW Δ}

_{one-line note: Moroccanoil CPM included. Booking volume + whether decline is spend-side or volume-side}_

━━ :warning: NETWORK-WIDE ADVERTISER SIGNALS ━━

_Spend DOWN:_
• Brand [NEA if applicable] — _−$X,XXX_ across N publishers · page-type concentration if notable

_Spend UP:_
• Brand [NEA if applicable] — _+$X,XXX_ across N publishers · page-type concentration if notable

_Total identified spend down: ~−$X · Total identified spend up: ~+$X · Net: ~−$X_
*Sent using* <@U0AGG5F5HEY>
"""

# Network signal rules:
# - Include ALL brands with abs(spend_delta) > $100 aggregated across publishers
# - publisher count = distinct publishers where brand had >$200 spend delta in that direction
# - Mark [NEA] if is_nea = true
# - Note page-type concentration if >50% of brand's delta is on one page type
# - If no brands have positive spend_delta > $100, write: "No brands with net spend increase above $100 threshold this week."
# - Spend DOWN section before Spend UP section
# - Always include total line at bottom


if __name__ == "__main__":
    current_start, current_end, prior_start, prior_end = get_report_window()
    print(f"Report window: {current_start} – {current_end} vs. {prior_start} – {prior_end}")
    print("To run: invoke via Claude Code with Hex MCP + Slack MCP + Gmail MCP")
    print(f"Slack channel: {REPORT_CONFIG['slack_channel_id']}")
    print(f"Email: {REPORT_CONFIG['email_to']}")
