"""Phone Pulse — Respondents overview page."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from src.data_loader import load_pp_respondents_profile, load_pp_village_stations

FEM_ORANGE = "#C1693A"
FEM_BROWN  = "#8B5E45"
FEM_NAVY   = "#2E3F52"
FEM_STEEL  = "#5A6E7F"
FEM_TAUPE  = "#7A7068"
GROUP_COLORS = {"Using FP": FEM_NAVY, "Not using FP": FEM_ORANGE, "All": FEM_TAUPE}

_CHART = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")


def _load() -> pd.DataFrame:
    return load_pp_respondents_profile()


AGE_GROUP_ORDER = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-45"]


def _hbar(df: pd.DataFrame, title: str, color: str = FEM_NAVY, category_order: list | None = None) -> go.Figure:
    if category_order:
        df = df.set_index("category").reindex(category_order).reset_index()
        df["pct"] = df["pct"].fillna(0)
    else:
        df = df.sort_values("pct")
    fig = go.Figure(go.Bar(
        x=df["pct"], y=df["category"], orientation="h",
        marker_color=color, text=df["pct"].map(lambda v: f"{v:.0f}%"),
        textposition="outside",
    ))
    fig.update_layout(
        **_CHART,
        title=title, xaxis_title="% of respondents", xaxis_range=[0, 110],
        height=max(200, 50 * len(df) + 80),
        margin=dict(l=10, r=30, t=40, b=10),
    )
    fig.update_yaxes(tickfont=dict(size=12), autorange="reversed" if category_order else True)
    return fig


def _row_count(df: pd.DataFrame, variable: str):
    row = df[df["variable"] == variable]
    if row.empty or pd.isna(row["count"].iloc[0]):
        return None
    return int(row["count"].iloc[0])


def render() -> None:
    df = _load()

    n_raw           = _row_count(df, "_n_raw")
    n_excl_quality  = _row_count(df, "_n_quality_excluded")
    n_after_qa      = _row_count(df, "_n_after_qa")
    n_no_radio      = _row_count(df, "_n_no_radio")
    n_radio_not_fem = _row_count(df, "_n_radio_not_fem")
    n_fem           = _row_count(df, "_n_fem_listeners")
    n_total         = _row_count(df, "_total") or "—"

    st.markdown("### Phone Pulse Survey — Respondents")

    if n_raw is not None:
        st.markdown("#### Sample funnel")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Raw submissions", n_raw)
        c2.metric("Excluded — quality", n_excl_quality,
                   delta=f"-{100*n_excl_quality/n_raw:.0f}%" if n_raw else None,
                   delta_color="inverse")
        c3.metric("Comparison (not FEM station)", n_no_radio + n_radio_not_fem if n_no_radio is not None and n_radio_not_fem is not None else None,
                   help="Not this page's analysis sample — see the Campaign Exposure page.")
        c4.metric("Treatment (this page's sample)", n_fem)
        st.caption(
            f"Of {n_raw} raw submissions, {n_excl_quality} were excluded for quality "
            f"concerns (duplicates, errors, nonresponse, placebo-station, dishonesty, "
            f"or not-a-radio-listener flags — see manual_flags.csv). Of the {n_after_qa} "
            f"that passed QA, this page covers only the {n_fem} FEM-partner-station "
            f"listeners (Treatment). The remaining {(n_no_radio or 0) + (n_radio_not_fem or 0)} "
            f"respondents (no radio, or radio but not a FEM station) are the Comparison "
            f"arm, analysed on the Campaign Exposure page."
        )
    else:
        st.metric("Total respondents (analysis sample)", n_total)
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        gender = df[df["variable"] == "gender"]
        if not gender.empty:
            fig = _hbar(gender, "Gender", FEM_BROWN)
            st.plotly_chart(fig, use_container_width=True)

        fp = df[df["variable"] == "fp_use"]
        if not fp.empty:
            fig = _hbar(fp, "Current FP use (fpbeh_fpnow)", FEM_NAVY)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        age = df[df["variable"] == "age_group"]
        if not age.empty:
            fig = _hbar(age, "Age", FEM_STEEL, category_order=AGE_GROUP_ORDER)
            st.plotly_chart(fig, use_container_width=True)

        pc = df[df["variable"] == "preg_chance"]
        if not pc.empty:
            fig = _hbar(pc, "Perceived pregnancy chance (fpbeh_pregchance)", FEM_ORANGE)
            st.plotly_chart(fig, use_container_width=True)

    # Village x station coverage map
    vs = load_pp_village_stations()
    if vs is not None and not vs.empty:
        st.markdown("#### Station coverage by village")
        st.caption(
            "Real FEM partner station(s) assigned to cover each village's settlement "
            "(from the roster, not listening behaviour). Villages with fewer than 5 "
            "respondents are suppressed for privacy."
        )
        vs_disp = vs.rename(
            columns={"village": "Village", "station": "Station", "n_respondents": "N respondents"}
        )
        st.dataframe(vs_disp, use_container_width=True, hide_index=True)
    elif vs is None:
        st.info(
            "Village x station coverage pending: run `export_pp_app_data.py`, upload "
            "`pp_village_stations.csv` to Drive, then paste its file ID into `data_loader.py`."
        )
