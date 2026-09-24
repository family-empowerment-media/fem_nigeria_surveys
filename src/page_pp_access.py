"""Phone Pulse — Access barriers page."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from src.data_loader import (
    load_pp_access_tried, load_pp_access_appointment, load_pp_access_got_wanted,
    load_pp_access_unavailable, load_pp_access_location, load_pp_access_distance,
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
    st.markdown("### Phone Pulse — Access Barriers")

    view = st.radio("View by", list(SPLIT_OPTIONS.keys()), horizontal=True, key="pp_access_split")
    split = SPLIT_OPTIONS[view]
    split_by, order, colors = split["split_by"], split["order"], split["colors"]

    st.caption(
        "Experiences seeking family planning services since the respondent's last "
        f"contact. Results broken down by {view.lower()}."
    )
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Tried to get contraception", "Got wanted method", "Where sought", "Travel time"
    ])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            df = _filter_split(load_pp_access_tried(), split_by)
            if df is None:
                _pending("pp_access_tried")
            else:
                st.plotly_chart(
                    _grouped_hbar(df, "Tried to get contraception since last contact", order, colors),
                    use_container_width=True,
                )
        with c2:
            df = _filter_split(load_pp_access_appointment(), split_by)
            if df is None:
                _pending("pp_access_appointment")
            else:
                st.plotly_chart(
                    _grouped_hbar(df, "Had a health appointment since last contact", order, colors),
                    use_container_width=True,
                )
                st.caption("Asked of respondents who had not tried to get contraception.")

    with tab2:
        df = _filter_split(load_pp_access_got_wanted(), split_by)
        if df is None:
            _pending("pp_access_got_wanted")
        else:
            st.plotly_chart(
                _grouped_hbar(df, "Got the wanted method when they tried", order, colors),
                use_container_width=True,
            )
            st.caption("Base: respondents who tried to get contraception.")

        st.markdown("#### What they did when the wanted method was unavailable")
        df = _filter_split(load_pp_access_unavailable(), split_by)
        if df is None:
            _pending("pp_access_unavailable")
        else:
            st.plotly_chart(
                _grouped_hbar(df, "Action taken when method was unavailable", order, colors),
                use_container_width=True,
            )
            st.caption("Base: respondents who did not get their wanted method.")

    with tab3:
        df = _filter_split(load_pp_access_location(), split_by)
        if df is None:
            _pending("pp_access_location")
        else:
            st.plotly_chart(
                _grouped_hbar(df, "Where respondents sought contraceptives", order, colors),
                use_container_width=True,
            )
            st.caption(
                "Base: respondents who tried to get contraception. "
                "Respondents may cite multiple locations."
            )

    with tab4:
        df = _filter_split(load_pp_access_distance(), split_by)
        if df is None:
            _pending("pp_access_distance")
        else:
            st.plotly_chart(
                _grouped_hbar(df, "Travel time to the health facility", order, colors),
                use_container_width=True,
            )
            st.caption("Base: respondents who tried to get contraception.")
