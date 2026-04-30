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

    # Hex projects
    "hex_publisher_alerts_project": "019d9be4-3547-7008-9849-742c0d956afb",
    "hex_supply_performance_project": "019ce306-f016-700c-aed9-a9ba95d827c2",

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
                "BOOKING GROUP": ["booking", "upcoming_booking"],
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
    "source": "FCT_BRAND_SESSIONS (no join to FCT_SESSIONS needed)",
    "group_by": ["publisher_name", "page_type", "brand_name", "is_nea", "brand_display_context"],
    "order_by": "abs(spend_delta) DESC",
    "limit_per_group": 5,
    "cross_publisher_signal_threshold": 3,  # Flag if top driver across >= 3 publishers
}


def get_report_window(as_of: datetime.date = None):
    """Return (current_start, current_end, prior_start, prior_end) for Mon–Sun weeks."""
    if as_of is None:
        as_of = datetime.date.today()
    # Find most recent Sunday (end of current week)
    days_since_sunday = (as_of.weekday() + 1) % 7
    current_end = as_of - datetime.timedelta(days=days_since_sunday)
    current_start = current_end - datetime.timedelta(days=6)
    prior_end = current_start - datetime.timedelta(days=1)
    prior_start = prior_end - datetime.timedelta(days=6)
    return current_start, current_end, prior_start, prior_end


if __name__ == "__main__":
    current_start, current_end, prior_start, prior_end = get_report_window()
    print(f"Report window: {current_start} – {current_end} vs. {prior_start} – {prior_end}")
    print("To run: invoke via Claude Code with Hex MCP + Slack MCP + Gmail MCP")
    print(f"Slack channel: {REPORT_CONFIG['slack_channel_id']}")
    print(f"Email: {REPORT_CONFIG['email_to']}")
