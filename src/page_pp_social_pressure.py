"""Phone Pulse — Social pressure & information sources page."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from src.data_loader import load_pp_religious_influence, load_pp_info_sources
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
}

_CHART = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")


def _pending(csv_name: str) -> None:
    st.info(
        f"Data pending: run `export_pp_app_data.py`, upload `{csv_name}.csv` to "
        f"Drive with link sharing on, then paste its file ID into `data_loader.py`."
    )


def _filter_split(df: pd.DataFrame | None, split_by: str) -> pd.DataFrame | None:
    if df is None or "split_by" not in df.columns:
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
    st.markdown("### Phone Pulse — Social Pressure & Information Sources")

    view = st.radio("View by", list(SPLIT_OPTIONS.keys()), horizontal=True, key="pp_social_pressure_split")
    split = SPLIT_OPTIONS[view]
    split_by, order, colors = split["split_by"], split["order"], split["colors"]

    st.caption(f"Results broken down by {view.lower()}.")
    st.markdown("---")

    tab1, tab2 = st.tabs(["Religious influence", "Information sources"])

    with tab1:
        df = _filter_split(load_pp_religious_influence(), split_by)
        if df is None:
            _pending("pp_religious_influence")
        else:
            st.plotly_chart(
                _grouped_hbar(df, "Degree religion influences FP decisions", order, colors),
                use_container_width=True,
            )

    with tab2:
        df = _filter_split(load_pp_info_sources(), split_by)
        if df is None:
            _pending("pp_info_sources")
        else:
            st.plotly_chart(
                _grouped_hbar(df, "Main sources of health information", order, colors),
                use_container_width=True,
            )
            st.caption("Respondents may cite multiple sources.")
