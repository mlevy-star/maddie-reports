#!/usr/bin/env python3
"""
Weekly Publisher Health Report Runner
Sends to: Slack #supply-health-weekly (C0AV8GH3EQ5) + email mlevy@disconetwork.com
Schedule: Daily at 9 AM (see cron.txt)
"""

import datetime

# Report configuration
REPORT_CONFIG = {
    "slack_channel_id": "C0AV8GH3EQ5",  # #supply-health-weekly
    "email_to": "mlevy@disconetwork.com",
    "email_subject_template": "📊 Weekly Publisher Health Report — {date}",

    # Hex projects
    "hex_supply_performance_project": "019ce306-f016-700c-aed9-a9ba95d827c2",

    # Page type mappings (raw DB value -> display label)
    "page_types": {
        "THANK_YOU": "TYP",
        "ORDER_STATUS": "OSP",
        "ORDER_TRACKING": "OTP",
        "SUPPORT_CENTER": "Support",
        # MODAL excluded
    },
}

# Report section order (RPM removed)
REPORT_SECTIONS = [
    "tldr",
    "rpl_all_pubs",
    "rpl_gopuff_bevmo",
    "rpl_mindbody",
    "network_advertiser_signals",
]

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

# RPL formula (Supply Performance)
RPL_FORMULA = "sum(billable_amount) / sum(sessions_with_widget_display)"

# Network-level advertiser attribution
# Aggregated across all publishers — shows which advertisers drove network-wide spend shifts
ATTRIBUTION = {
    "source": "FCT_BRAND_SESSIONS",
    "group_by": ["brand_name", "is_nea", "brand_display_context"],
    "cross_publisher_signal_threshold": 3,  # Include if spend moved at >= 3 publishers
    "include_totals": True,                 # Show total spend down / up / net
}


def get_report_window(as_of: datetime.date = None):
    """Return (current_start, current_end, prior_start, prior_end) as rolling 7-day windows.

    current  = [today-7 .. yesterday]
    prior    = [today-14 .. today-8]
    Windows are day-of-week-agnostic per spec.
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
