"""Phone Pulse — Media (TV, Radio detail, Socials) page."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from src.data_loader import (
    load_pp_tv_any, load_pp_tv_hours, load_pp_tv_topics, load_pp_tv_uptake,
    load_pp_radio_device, load_pp_radio_station_frequency, load_pp_radio_topics,
    load_pp_radio_fp_freq, load_pp_radio_conversation, load_pp_radio_broadcast_opinion,
    load_pp_social_any, load_pp_social_hours, load_pp_social_uptake,
)

FEM_ORANGE = "#C1693A"
FEM_NAVY   = "#2E3F52"
FEM_TAUPE  = "#7A7068"
FEM_BROWN  = "#8B5E45"
FEM_STEEL  = "#5A6E7F"

SPLIT_OPTIONS = {
    "FP use status": {
        "split_by": "fp_use",
        "order":  ["Using FP", "Not using FP", "All"],
        "colors": {"Using FP": FEM_NAVY, "Not using FP": FEM_ORANGE, "All": FEM_TAUPE},
    },
    "Gender": {
        "split_by": "gender",
        "order":  ["Male", "Female", "All"],
        "colors": {"Male": FEM_STEEL, "Female": FEM_BROWN, "All": FEM_TAUPE},
    },
    "Treatment / Comparison": {
        "split_by": "treatment_arm",
        "order":  ["Treatment", "Comparison", "All"],
        "colors": {"Treatment": FEM_NAVY, "Comparison": FEM_ORANGE, "All": FEM_TAUPE},
    },
}

_CHART = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")


def _pending(csv_name: str) -> None:
    st.info(
        f"Data pending: run `export_pp_app_data.py`, upload `{csv_name}.csv` to "
        f"Drive with link sharing on, then paste its file ID into "
        f"`data_loader.py` (`load_{csv_name.replace('pp_', 'pp_')}`)."
    )


def _filter_split(df: pd.DataFrame | None, split_by: str) -> pd.DataFrame | None:
    if df is None or "split_by" not in df.columns:
        return df
    return df[df["split_by"] == split_by]


def _grouped_hbar(df: pd.DataFrame, title: str, group_order: list, group_colors: dict,
                  xmax: float = 100) -> go.Figure:
    fig = go.Figure()
    df = df[df["category"].notna()]
    n_cats = df["category"].nunique()
    for grp in group_order:
        sub = df[df["group"] == grp].sort_values("pct")
        if sub.empty:
            continue
        fig.add_trace(go.Bar(
            x=sub["pct"], y=sub["category"], orientation="h",
            name=grp, marker_color=group_colors[grp],
            text=sub["pct"].map(lambda v: f"{v:.0f}%"),
            textposition="outside",
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
    return fig


def _per_station_chart(df: pd.DataFrame, title: str, key: str, group_order: list, group_colors: dict) -> None:
    """df has columns: group, station, category, count, pct, n_assigned, n_listened.
    n_assigned/n_listened are attached to the "All" group's rows (or the
    first available group) as station-level context, since a station with
    no listeners produces no category rows at all."""
    stations = sorted(df["station"].dropna().unique())
    if not stations:
        st.info("No station data available.")
        return
    station = st.selectbox("Station", stations, key=key)
    sub = df[df["station"] == station]

    meta_rows = sub[sub["group"] == "All"]
    meta = meta_rows.iloc[0] if not meta_rows.empty else (sub.iloc[0] if not sub.empty else None)
    n_assigned = int(meta["n_assigned"]) if meta is not None and pd.notna(meta.get("n_assigned")) else None
    n_listened = int(meta["n_listened"]) if meta is not None and pd.notna(meta.get("n_listened")) else None

    if sub["category"].notna().any():
        fig = _grouped_hbar(sub, f"{title} — {station}", group_order, group_colors)
        st.plotly_chart(fig, use_container_width=True)
        if n_assigned is not None:
            st.caption(f"{n_listened} of {n_assigned} respondents assigned to this station reported listening to it at all.")
    elif n_assigned is not None:
        st.info(
            f"No respondents assigned to {station} reported listening to it "
            f"({n_listened} of {n_assigned} assigned), so there's no listening-frequency "
            f"breakdown to show."
        )
    else:
        st.info("No data available for this station.")


def _by_question_charts(df: pd.DataFrame, group_order: list, group_colors: dict) -> None:
    """df has columns: group, question, category, count, pct — one chart per question."""
    if df.empty:
        st.info("No data available.")
        return
    for question in df["question"].dropna().unique():
        sub = df[df["question"] == question]
        fig = _grouped_hbar(sub, question, group_order, group_colors)
        st.plotly_chart(fig, use_container_width=True)


def render() -> None:
    st.markdown("### Phone Pulse — Media (TV, Radio detail, Socials)")

    view = st.radio("View by", list(SPLIT_OPTIONS.keys()), horizontal=True, key="pp_media_split")
    split = SPLIT_OPTIONS[view]
    split_by, order, colors = split["split_by"], split["order"], split["colors"]

    caption = f"Results broken down by {view.lower()}."
    if view == "Treatment / Comparison":
        caption += (
            " Note: this view uses a DIFFERENT, larger population than the other two "
            "(all 509 QA-passed respondents, not just the 414 Treatment/FEM-station "
            "listeners) — Treatment = FEM partner station listener, Comparison = "
            "everyone else (see the Campaign Exposure page for the full definition)."
        )
    st.caption(caption)
    st.markdown("---")

    tv_tab, radio_tab, social_tab = st.tabs(["TV", "Radio (detail)", "Socials"])

    # ── TV ────────────────────────────────────────────────────────────────
    with tv_tab:
        c1, c2 = st.columns(2)
        with c1:
            df = _filter_split(load_pp_tv_any(), split_by)
            if df is None:
                _pending("pp_tv_any")
            elif df.empty:
                st.info("No TV viewership recorded in this wave.")
            else:
                st.plotly_chart(_grouped_hbar(df, "Watched TV in past month", order, colors),
                                 use_container_width=True)
        with c2:
            df = _filter_split(load_pp_tv_uptake(), split_by)
            if df is None:
                _pending("pp_tv_uptake")
            elif df.empty:
                st.info("No data available.")
            else:
                st.plotly_chart(_grouped_hbar(df, "Remember MCH/birth-spacing content on TV", order, colors),
                                 use_container_width=True)

        df = _filter_split(load_pp_tv_hours(), split_by)
        if df is None:
            _pending("pp_tv_hours")
        elif df.empty:
            st.info("No TV-hours data recorded in this wave (too few viewers, or field blank).")
        else:
            st.plotly_chart(_grouped_hbar(df, "Daily TV hours (among viewers)", order, colors),
                             use_container_width=True)

        df = _filter_split(load_pp_tv_topics(), split_by)
        if df is None:
            _pending("pp_tv_topics")
        elif df.empty:
            st.info("No TV-topics data recorded in this wave.")
        else:
            st.plotly_chart(_grouped_hbar(df, "Topics watched on TV (among viewers)", order, colors),
                             use_container_width=True)
            st.caption("Base: TV viewers only. Respondents may cite multiple topics.")

    # ── Radio detail ─────────────────────────────────────────────────────
    with radio_tab:
        st.caption("Additional radio detail beyond the main Radio page: device, "
                    "per-station frequency, topics, and conversation/opinion items.")

        df = _filter_split(load_pp_radio_device(), split_by)
        if df is None:
            _pending("pp_radio_device")
        else:
            st.plotly_chart(_grouped_hbar(df, "Device used to listen to radio (among listeners)", order, colors),
                             use_container_width=True)

        df = _filter_split(load_pp_radio_topics(), split_by)
        if df is None:
            _pending("pp_radio_topics")
        else:
            st.plotly_chart(_grouped_hbar(df, "Topics heard on radio (among listeners)", order, colors),
                             use_container_width=True)
            st.caption("Base: radio listeners only. Respondents may cite multiple topics.")

        st.markdown("#### Per-station listening frequency")
        df = _filter_split(load_pp_radio_station_frequency(), split_by)
        if df is None:
            _pending("pp_radio_station_frequency")
        else:
            _per_station_chart(df, "Listening frequency", "freq_station", order, colors)

        st.markdown("#### Per-station FP/MCH content frequency")
        df = _filter_split(load_pp_radio_fp_freq(), split_by)
        if df is None:
            _pending("pp_radio_fp_freq")
        else:
            _per_station_chart(df, "Frequency of hearing FP/MCH content", "fp_freq_station", order, colors)

        st.markdown("#### Conversations about FP/MCH content")
        df = _filter_split(load_pp_radio_conversation(), split_by)
        if df is None:
            _pending("pp_radio_conversation")
        else:
            _by_question_charts(df, order, colors)

        st.markdown("#### Opinion on broadcast frequency & repeat behaviour")
        df = _filter_split(load_pp_radio_broadcast_opinion(), split_by)
        if df is None:
            _pending("pp_radio_broadcast_opinion")
        else:
            _by_question_charts(df, order, colors)

    # ── Socials ──────────────────────────────────────────────────────────
    with social_tab:
        c1, c2 = st.columns(2)
        with c1:
            df = _filter_split(load_pp_social_any(), split_by)
            if df is None:
                _pending("pp_social_any")
            elif df.empty:
                st.info("No social media usage recorded in this wave.")
            else:
                st.plotly_chart(_grouped_hbar(df, "Used social media in past month", order, colors),
                                 use_container_width=True)
        with c2:
            df = _filter_split(load_pp_social_uptake(), split_by)
            if df is None:
                _pending("pp_social_uptake")
            elif df.empty:
                st.info("No data available.")
            else:
                st.plotly_chart(_grouped_hbar(df, "Remember MCH/birth-spacing content on social media", order, colors),
                                 use_container_width=True)

        df = _filter_split(load_pp_social_hours(), split_by)
        if df is None:
            _pending("pp_social_hours")
        elif df.empty:
            st.info("No social-media-hours data recorded in this wave.")
        else:
            st.plotly_chart(_grouped_hbar(df, "Daily social media hours (among users)", order, colors),
                             use_container_width=True)
