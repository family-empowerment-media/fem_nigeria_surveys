"""Phone Pulse — Partner dynamics & social norms page."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from src.data_loader import (
    load_pp_partner_decision,
    load_pp_partner_norms,
    load_pp_partner_discuss,
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
}

_CHART = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")


def _filter_split(df: pd.DataFrame, split_by: str) -> pd.DataFrame:
    if "split_by" not in df.columns:
        return df
    return df[df["split_by"] == split_by]


def _grouped_hbar(df: pd.DataFrame, title: str, group_order: list, group_colors: dict,
                  xmax: float = 100) -> go.Figure:
    fig = go.Figure()
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


def render() -> None:
    st.markdown("### Phone Pulse — Partner Dynamics & Social Norms")

    view = st.radio("View by", list(SPLIT_OPTIONS.keys()), horizontal=True, key="pp_partner_split")
    split = SPLIT_OPTIONS[view]
    split_by, order, colors = split["split_by"], split["order"], split["colors"]

    st.caption(f"Results broken down by {view.lower()}.")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["FP decision-making", "Social norms", "Discussion norms"])

    with tab1:
        df = _filter_split(load_pp_partner_decision(), split_by)
        fig = _grouped_hbar(df, "Who decides about family planning? (partner_pressure)", order, colors)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "1 = Mainly respondent, 2 = Mainly spouse, 3 = Joint decision, "
            "4 = Other / not applicable."
        )

    with tab2:
        df = _filter_split(load_pp_partner_norms(), split_by)
        if df.empty:
            st.info("No norm data available.")
        else:
            fig = go.Figure()
            for grp in order:
                sub = df[df["group"] == grp].dropna(subset=["mean"])
                if sub.empty:
                    continue
                fig.add_trace(go.Bar(
                    x=sub["mean"], y=sub["label"], orientation="h",
                    name=grp, marker_color=colors[grp],
                    text=sub["mean"].map(lambda v: f"{v:.2f}"),
                    textposition="outside",
                ))
            fig.update_layout(
                **_CHART,
                title="Mean agreement with social norm statements (0–4 scale)",
                barmode="group",
                xaxis_title="Mean agreement (0 = Strongly disagree, 4 = Strongly agree)",
                xaxis_range=[0, 5],
                height=375,
                margin=dict(l=10, r=30, t=78, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.15),
            )
            fig.add_vline(x=2, line_dash="dot", line_color="#aaa")
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Statements rated 0–4 (0 = Strongly disagree, 4 = Strongly agree). "
                "Dashed line at 2 = neutral midpoint."
            )

    with tab3:
        df = _filter_split(load_pp_partner_discuss(), split_by)
        fig = _grouped_hbar(
            df, 'Agreement: "Not acceptable to discuss FP with friends" (pressure_discuss)',
            order, colors,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Scale: 0 = Strongly disagree, 1 = Disagree, 2 = Neither, "
            "3 = Agree, 4 = Strongly agree."
        )
