import streamlit as st
from src.page_stubs import stub_card

# 2026-09-10: pulled out of the Phone Pulse tab and promoted to a top-level
# "home page" (see app.py) per the user's request -- this is meant to be the
# first thing anyone lands on, framing the whole survey program (baseline +
# phone pulse follow-ups at 3/6/24 months) as ONE time series, viewed two
# ways:
#   Cross-sectional -- each wave's own (independent) respondents, compared
#                      wave-over-wave as population-level snapshots.
#   Longitudinal    -- only the panel members present in every wave, same
#                      individuals tracked across time.
# Benin has fielded baseline only -- no phone pulse wave exists yet (see
# data_loader.py's "Phone Pulse pages" note, and page_stubs.py, which this
# reuses _stub_card from). So every section below is structural: the mode
# toggle, wave axis, and three metric groups are real and meant to stay
# fixed, but their content is a stub until phone-pulse ETL/data exists --
# same "real navigation, stubbed content" convention as the rest of Phone
# Pulse, not a set of loaders that would always return None.

WAVES = ["Baseline", "3 months", "6 months", "24 months"]

MODE_DESCRIPTIONS = {
    "Cross-sectional": (
        "Each wave's own respondents (baseline sample, then each phone pulse "
        "follow-up's own sample) compared as independent population-level "
        "snapshots -- shows how the population overall is moving, not "
        "whether any individual changed."
    ),
    "Longitudinal": (
        "Only respondents present in every wave (the phone pulse panel), "
        "tracked across time -- shows whether the SAME people's awareness, "
        "attitudes, and barriers changed, not just the population mix."
    ),
}

# Each metric section becomes one time-series chart per mode once data
# exists: x-axis = WAVES, y-axis = the metric, one line per sub-category
# (e.g. one line per method for awareness, one per statement for attitudes).
METRIC_SECTIONS = [
    {
        "title": "Awareness of methods",
        "description": (
            "Share of respondents aware of each contraceptive method, by wave. "
            "Cross-sectional: population awareness overall. Longitudinal: "
            "whether panel members' own awareness grew."
        ),
        "fields": ["method_awareness_*", "wave", "respondent_id (longitudinal only)"],
    },
    {
        "title": "Attitudes toward family planning",
        "description": (
            "Agreement with the core attitude statements (same statements as "
            "the baseline Agreement & Characteristics page), tracked by wave "
            "to see whether attitudes shift after phone pulse exposure."
        ),
        "fields": ["statement_1..N", "wave", "respondent_id (longitudinal only)"],
    },
    {
        "title": "Family planning barriers",
        "description": (
            "Supply (stockouts), accessibility (travel), and affordability "
            "barriers -- same three components as the baseline Access & "
            "Supply page -- tracked by wave to see whether barriers ease."
        ),
        "fields": ["reason_nonuse_main", "stockouts_*", "travel_time_*", "wave"],
    },
]


def render():
    st.header("Baseline vs. Follow-up")
    st.caption(
        "Time series across the full survey program -- baseline plus phone pulse "
        "follow-ups at 3, 6, and 24 months -- for awareness of methods, attitudes, "
        "and family planning barriers."
    )

    mode = st.radio(
        "Compare as:",
        list(MODE_DESCRIPTIONS.keys()),
        horizontal=True,
        help="Cross-sectional = independent samples per wave. Longitudinal = same panel, tracked over time.",
    )
    st.caption(MODE_DESCRIPTIONS[mode])

    st.markdown(
        "**Waves:** " + " → ".join(WAVES)
        + ("  *(panel members only)*" if mode == "Longitudinal" else "  *(each wave's own respondents)*")
    )

    st.divider()
    st.info(
        "No phone pulse follow-up has been fielded for Benin yet -- baseline is the "
        "only wave with data. The three sections below are ready to populate once a "
        "follow-up wave and its ETL pipeline exist (mirroring niger_app/src/page_pp_*.py "
        "and pipeline_output's etl_pp_*.py, neither of which exist for Benin yet)."
    )

    for section in METRIC_SECTIONS:
        stub_card(
            f"{section['title']} ({mode})",
            section["description"],
            section["fields"],
        )
