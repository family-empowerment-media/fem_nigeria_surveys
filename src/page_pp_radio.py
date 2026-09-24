"""Phone Pulse — Radio listenership page."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from src.data_loader import (
    load_pp_radio_any,
    load_pp_radio_uptake,
    load_pp_radio_days,
    load_pp_radio_hours,
    load_pp_radio_stations,
)

from src.fem_colours import FEM_ORANGE, FEM_NAVY, FEM_TAUPE, FEM_BROWN, FEM_STEEL

SPLIT_OPTIONS = {
    "FP use status": {
        "split_by": "fp_use",
        "order":  ["Using FP", "Not using FP", "All"],
        "colors": {"Using FP": FEM_STEEL, "Not using FP": FEM_BROWN, "All": FEM_TAUPE},
    },
    "Gender": {
        "split_by": "gender",
        "order":  ["Male", "Female", "All"],
        "colors": {"Male": FEM_NAVY, "Female": FEM_ORANGE, "All": FEM_TAUPE},
    },
    "Treatment / Comparison": {
        "split_by": "treatment_arm",
        "order":  ["Treatment", "Comparison", "All"],
        "colors": {"Treatment": FEM_STEEL, "Comparison": FEM_BROWN, "All": FEM_TAUPE},
    },
}

_CHART = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")


def _filter_split(df: pd.DataFrame, split_by: str) -> pd.DataFrame:
    """Filter a df to one split dimension. Older/cached exports without a
    split_by column (pre-gender-slicing) are passed through unfiltered."""
    if "split_by" not in df.columns:
        return df
    return df[df["split_by"] == split_by]


def _grouped_hbar(df: pd.DataFrame, title: str, group_order: list, group_colors: dict,
                  xmax: float = 100, caption: str = "") -> None:
    fig = go.Figure()
    n_cats = df["category"].nunique()
    has_n = "n_assigned" in df.columns
    has_nr = "n_no_response" in df.columns
    for grp in group_order:
        sub = df[df["group"] == grp].sort_values("pct")
        if sub.empty:
            continue
        trace_kw = {}
        if has_n and has_nr:
            trace_kw["customdata"] = sub[["n_assigned", "n_no_response"]].to_numpy()
            trace_kw["hovertemplate"] = (
                "%{y}: %{x:.1f}%% (%{customdata[0]:.0f} assigned; "
                "%{customdata[1]:.0f} did not answer)<extra>%{fullData.name}</extra>"
            )
        elif has_n:
            trace_kw["customdata"] = sub[["n_assigned"]].to_numpy()
            trace_kw["hovertemplate"] = (
                "%{y}: %{x:.1f}%% (%{customdata[0]:.0f} assigned to this station)<extra>%{fullData.name}</extra>"
            )
        fig.add_trace(go.Bar(
            x=sub["pct"], y=sub["category"], orientation="h",
            name=grp, marker_color=group_colors[grp],
            text=sub["pct"].map(lambda v: f"{v:.0f}%"),
            textposition="outside",
            **trace_kw,
        ))
    fig.update_layout(
        **_CHART,
        title=title, barmode="group",
        xaxis_title="% of respondents",
        xaxis_range=[0, xmax + 15],
        height=max(250, 35 * n_cats * len(group_order) + 100),
        margin=dict(l=10, r=30, t=78, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.15, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)
    if caption:
        st.caption(caption)


def render() -> None:
    st.markdown("### Phone Pulse — Radio Listenership")

    view = st.radio("View by", list(SPLIT_OPTIONS.keys()), horizontal=True, key="pp_radio_split")
    split = SPLIT_OPTIONS[view]
    split_by, order, colors = split["split_by"], split["order"], split["colors"]

    caption = f"Results broken down by {view.lower()}. Base for station / hours / days charts: radio listeners only."
    if view == "Treatment / Comparison":
        caption += (
            " Note: this view uses a DIFFERENT, larger population than the other two "
            "(all 509 QA-passed respondents, not just the 414 Treatment/FEM-station "
            "listeners) — Treatment = FEM partner station listener, Comparison = "
            "everyone else (see the Campaign Exposure page for the full definition)."
        )
    st.caption(caption)
    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Listenership", "FP content heard", "Listening days",
        "Daily hours", "Stations"
    ])

    with tab1:
        df = _filter_split(load_pp_radio_any(), split_by)
        _grouped_hbar(df, "Radio listenership", order, colors,
                      caption="Base: all respondents.")

    with tab2:
        df = _filter_split(load_pp_radio_uptake(), split_by)
        _grouped_hbar(df, "Heard FP content on radio", order, colors,
                      caption="Base: all respondents.")

    with tab3:
        df = _filter_split(load_pp_radio_days(), split_by)
        _grouped_hbar(df, "Days of the week listeners tune in", order, colors,
                      caption="Base: radio listeners only.")

    with tab4:
        df = _filter_split(load_pp_radio_hours(), split_by)
        # Vertical bar for ordered buckets
        fig = go.Figure()
        hour_order = ["<1 hr", "1 hr", "2 hrs", "3 hrs", "4 hrs", "5–6 hrs", "7+ hrs"]
        for grp in order:
            sub = df[df["group"] == grp].copy()
            sub["_ord"] = sub["category"].map({v: i for i, v in enumerate(hour_order)})
            sub = sub.sort_values("_ord")
            if sub.empty:
                continue
            fig.add_trace(go.Bar(
                x=sub["category"], y=sub["pct"],
                name=grp, marker_color=colors[grp],
                text=sub["pct"].map(lambda v: f"{v:.0f}%"),
                textposition="outside",
            ))
        fig.update_layout(
            **_CHART,
            title="Daily listening hours (among radio listeners)",
            barmode="group", yaxis_title="% of listeners",
            yaxis_range=[0, 80],
            height=405,
            margin=dict(l=10, r=10, t=78, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.15),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Base: radio listeners only.")

    with tab5:
        df = _filter_split(load_pp_radio_stations(), split_by)
        title = "Station listenership (among respondents assigned to that station)"
        _grouped_hbar(
            df, title, order, colors,
            caption=(
                "Base for each station's % is respondents ASSIGNED to that station "
                "(it covers their settlement) — not all respondents, and not the same "
                "denominator per station. Hover a bar to see how many respondents that "
                "station was assigned to, and how many left the listening question "
                "blank (\"did not answer\") rather than answering \"No\" — a 0% with a "
                "high did-not-answer count isn't the same result as a 0% where everyone "
                "actually answered \"No\". A 100% on a station assigned to only 1-2 "
                "people isn't a strong result either. Placebo (non-partner control) "
                "stations are excluded here — see the Media page for per-respondent "
                "placebo detail."
            ),
        )
