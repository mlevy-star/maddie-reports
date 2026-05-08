#!/usr/bin/env python3
"""
Weekly Publisher Health Report — Configuration & Spec
Schedule: Every day at 9:00 AM ET (see cron.txt / run_report.sh)
Delivery: Slack #supply-health-weekly + email mlevy@disconetwork.com
"""

import datetime

REPORT_CONFIG = {
    "slack_channel_id":   "C0AV8GH3EQ5",   # #supply-health-weekly
    "slack_mention_user": "U0AGG5F5HEY",
    "email_to":           "mlevy@disconetwork.com",
    "email_subject_template": "📊 Weekly Publisher Health Report — {date}",

    # Hex
    "hex_supply_performance_project": "019ce306-f016-700c-aed9-a9ba95d827c2",
    "hex_supply_performance_url": (
        "https://app.hex.tech/01975719-79d0-711b-a61c-0d574da7873a"
        "/app/Supply-Performance-032glc8YVtMzC5RWVsOqqQ/latest"
    ),

    # RPL health flag thresholds (WoW %)
    "thresholds": {
        "critical": -0.20,   # drop > 20%
        "at_risk":  -0.10,   # drop 10–20%
        "increase":  0.10,   # gain > 10%
        # else: HEALTHY (±10%)
    },

    # Page type mappings (raw DB value -> display label); MODAL always excluded
    "page_types": {
        "THANK_YOU":      "TYP",
        "ORDER_STATUS":   "OSP",
        "ORDER_TRACKING": "OTP",
        "SUPPORT_CENTER": "Support",
    },

    # Advertiser signal display / inclusion thresholds
    "spend_down_display_threshold":    -500,   # list in Spend DOWN if spend_delta <= -$500
    "spend_up_display_threshold":       100,   # list in Spend UP if spend_delta > +$100
    "abs_threshold_for_totals":         100,   # include brand in totals if abs(delta) > $100
    "publisher_count_threshold":        200,   # count publisher if |brand spend delta| > $200
    "page_type_concentration_pct":     0.50,   # flag if single page type drives > 50% of delta
    "large_brand_breakdown_threshold":  500,   # get publisher breakdown if abs(delta) > $500
}


# ─── Rolling window (always relative to today) ────────────────────────────────
# current : (today − 7) through (today − 1)   [7 days ending yesterday]
# prior   : (today − 14) through (today − 8)  [7 days before current]
def get_report_window(as_of: datetime.date = None):
    """Return (current_start, current_end, prior_start, prior_end)."""
    if as_of is None:
        as_of = datetime.date.today()
    current_end   = as_of - datetime.timedelta(days=1)
    current_start = as_of - datetime.timedelta(days=7)
    prior_end     = as_of - datetime.timedelta(days=8)
    prior_start   = as_of - datetime.timedelta(days=14)
    return current_start, current_end, prior_start, prior_end


# ─── Publisher Segments ────────────────────────────────────────────────────────
SEGMENTS = {
    "section_a_all_pubs": {
        "description": "All publishers excluding Mindbody, Gopuff, BevMo",
        "exclude": ["Mindbody", "Gopuff", "BevMo"],
        "source_tables": ["FCT_SESSIONS", "FCT_BRAND_SESSIONS"],
        "join_key": "session_id",
    },
    "section_b_gopuff_bevmo": {
        "description": "Gopuff and BevMo",
        "include": ["Gopuff", "BevMo"],
        "source_tables": ["FCT_SESSIONS", "FCT_BRAND_SESSIONS"],
        "join_key": "session_id",
        "segment_label_field": "publisher_name",  # show Gopuff vs BevMo rows separately
    },
    "section_c_mindbody": {
        "description": "Mindbody — custom pipeline",
        "include": ["Mindbody"],
        "source_tables": [
            "reporting.event",
            "reporting.combined_cpc_cpa_ad_spend_revenue",
        ],
        "pipeline": {
            # Keep only the first event per order_id (ad-ops dedup)
            "deduplication": (
                "lag() over (partition by order_id order by event_created_at) — "
                "keep only rows where lag is NULL (first event per order)"
            ),
            # Moroccanoil CPM surcharge on top of standard billable_amount
            "moroccanoil_cpm": (
                "impressions * $0.10 from widget_viewable_threshold_brand_display "
                "events for Moroccanoil — add to billable_amount"
            ),
            # Two action groups reported
            "action_groups": {
                "BOOKING GROUP":  ["booking", "upcoming_booking"],
                "PURCHASE GROUP": ["purchase", "booking_and_purchase", "purchase_and_booking"],
            },
            "rpl_denominator": "deduplicated session count (widget_load events, first per order_id)",
            "rpl_numerator":   "sum(billable_amount) + Moroccanoil CPM adjustment",
        },
        "wow_note": (
            "compare ad_ops session count WoW to identify spend-side "
            "(count flat/up, spend fell) vs volume-side (count fell) moves"
        ),
    },
}

# ─── Core Formulas ────────────────────────────────────────────────────────────
RPL_FORMULA   = "sum(billable_amount) / nullif(sum(sessions_with_widget_display), 0)"
RPL_WOW_DELTA = "(current_rpl - prior_rpl) / nullif(prior_rpl, 0)"
DFL_METRIC    = "sum(sessions_with_widget_display)"  # demand-fill-level; direction = demand vs supply signal

# ─── Advertiser Attribution (Step 2) ──────────────────────────────────────────
ATTRIBUTION = {
    "source": "FCT_BRAND_SESSIONS joined to FCT_SESSIONS on session_id",
    "exclude_publishers": ["Mindbody"],
    # IMPORTANT: brand_display_context must be in GROUP BY to avoid double-counting
    # Hero vs Multiple placement spend for the same brand/session
    "group_by": ["brand_name", "is_nea", "brand_display_context"],
    "spend_delta_formula": "sum(current billable_amount) - sum(prior billable_amount)",
    "publisher_count_definition": (
        "count of distinct publishers where abs(spend delta for that brand on that publisher) > $200"
    ),
    "publisher_breakdown": (
        "for brands where abs(total spend_delta) > $500, "
        "show top publishers sorted by spend delta and note page-type concentration"
    ),
    "sort_order": "spend_delta ASC (most negative first)",
}


if __name__ == "__main__":
    cs, ce, ps, pe = get_report_window()
    print(f"Current window : {cs} — {ce}")
    print(f"Prior window   : {ps} — {pe}")
    print(f"Slack channel  : {REPORT_CONFIG['slack_channel_id']}")
    print(f"Email          : {REPORT_CONFIG['email_to']}")
