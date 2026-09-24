"""Phone Pulse — Attitudes toward FP page."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from src.data_loader import load_pp_attitudes, load_pp_info_perceptions

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

SCALE_NOTE = (
    "Scale: 0 = Strongly disagree → 4 = Strongly agree. "
    "Higher scores indicate stronger agreement with the statement."
)

QUESTION_CATEGORY_ORDER = {
    "When can a woman become pregnant again after delivery?": [
        "Immediately / within days", "Within the first month",
        "1–3 months after delivery", "4–6 months after delivery",
        "6–12 months after delivery", "More than a year", "It depends",
    ],
    "Likelihood FP methods make it harder for a woman to get pregnant later": [
        "Very likely", "Somewhat likely", "Neither likely nor unlikely",
        "Unlikely", "Very unlikely",
    ],
    "Likelihood a woman's menstrual cycle changes or stops while using FP": [
        "Very likely", "Somewhat likely", "Neither likely nor unlikely",
        "Unlikely", "Very unlikely",
    ],
    "Recommended wait after giving birth before trying to conceive again": [
        "At least 6 months", "At least one year", "At least two years", "At least 4 years",
    ],
}

# Notes shown under specific questions — only where there's a well-established
# correct answer / myth to call out; the other two items are purely descriptive.
QUESTION_NOTES = {
    "Likelihood FP methods make it harder for a woman to get pregnant later": (
        "FP methods do not cause long-term infertility — this is a well-documented "
        "myth, not a real side effect. \"Very likely\"/\"Somewhat likely\" answers "
        "reflect the misconception."
    ),
    "Recommended wait after giving birth before trying to conceive again": (
        "WHO recommends waiting at least 24 months after a live birth before the "
        "next pregnancy — \"At least two years\" is the medically correct answer."
    ),
}


def _info_perception_chart(df: pd.DataFrame, question: str, group_order: list, group_colors: dict):
    sub = df[df["question"] == question]
    if sub.empty:
        return None
    order = QUESTION_CATEGORY_ORDER.get(question)
    fig = go.Figure()
    for grp in group_order:
        g = sub[sub["group"] == grp]
        if g.empty:
            continue
        if order:
            g = g.set_index("category").reindex(order).reset_index()
            g["pct"] = g["pct"].fillna(0)
        fig.add_trace(go.Bar(
            x=g["pct"], y=g["category"], orientation="h",
            name=grp, marker_color=group_colors[grp],
            text=g["pct"].map(lambda v: f"{v:.0f}%" if pd.notna(v) else ""),
            textposition="outside",
        ))
    n_cats = len(order) if order else sub["category"].nunique()
    fig.update_layout(
        **_CHART,
        title=question, barmode="group",
        xaxis_title="% of respondents", xaxis_range=[0, 115],
        height=max(260, 32 * n_cats * len(group_order) + 100),
        margin=dict(l=10, r=30, t=78, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.15, xanchor="right", x=1),
    )
    if order:
        fig.update_yaxes(categoryorder="array", categoryarray=list(reversed(order)))
    return fig


def _filter_split(df: pd.DataFrame, split_by: str) -> pd.DataFrame:
    if "split_by" not in df.columns:
        return df
    return df[df["split_by"] == split_by]


def _dot_chart(df: pd.DataFrame, title: str, group_order: list, group_colors: dict) -> go.Figure:
    """Lollipop-style dot chart: one row per attitude item, dots per group."""
    fig = go.Figure()
    for grp in group_order:
        sub = df[df["group"] == grp]
        fig.add_trace(go.Scatter(
            x=sub["mean"], y=sub["label"],
            mode="markers+text", name=grp,
            marker=dict(color=group_colors[grp], size=12),
            text=sub["mean"].map(lambda v: f"{v:.2f}" if pd.notna(v) else ""),
            textposition="middle right",
        ))
    fig.update_layout(
        **_CHART,
        title=title,
        xaxis=dict(title="Mean agreement score (0–4)", range=[-0.2, 5.5]),
        height=max(300, 50 * df["label"].nunique() + 120),
        margin=dict(l=10, r=10, t=78, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.15),
    )
    fig.add_vline(x=2, line_dash="dot", line_color="#aaa")   # neutral midpoint
    return fig


def render() -> None:
    try:
        df = load_pp_attitudes()
    except Exception:
        st.error("Attitude data not found. Re-run export_pp_app_data.py.")
        return

    st.markdown("### Phone Pulse — Attitudes toward Family Planning")

    view = st.radio("View by", list(SPLIT_OPTIONS.keys()), horizontal=True, key="pp_attitudes_split")
    split = SPLIT_OPTIONS[view]
    split_by, order, colors = split["split_by"], split["order"], split["colors"]
    df = _filter_split(df, split_by)

    st.caption(
        "Mean agreement scores on 8 attitude statements, rated 0–4 (0 = Strongly disagree, "
        f"4 = Strongly agree), broken down by {view.lower()}. Dashed line at 2 = neutral."
    )
    st.markdown("---")

    tab_self, tab_spouse, tab_commu, tab_knowledge = st.tabs(
        ["Own attitudes", "Perceived spouse attitudes", "Perceived community attitudes",
         "Knowledge & Perceptions"]
    )

    for tab, perspective, label in [
        (tab_self,  "self",      "own"),
        (tab_spouse,"spouse",   "spouse's"),
        (tab_commu, "community","community's"),
    ]:
        with tab:
            sub = df[df["perspective"] == perspective].dropna(subset=["mean"])
            if sub.empty:
                st.info(f"No data available for {label} attitudes.")
                continue

            fig = _dot_chart(sub, f"Mean agreement — {label.capitalize()} attitudes", order, colors)
            st.plotly_chart(fig, use_container_width=True)
            st.caption(SCALE_NOTE)

            # Summary table
            pivot = sub.pivot_table(
                index="label", columns="group", values="mean", aggfunc="first"
            ).reset_index()
            col_order = ["label"] + [g for g in order if g in pivot.columns]
            pivot = pivot[col_order]
            for g in order:
                if g in pivot.columns:
                    pivot[g] = pivot[g].map(lambda v: f"{v:.2f}" if pd.notna(v) else "—")
            pivot = pivot.rename(columns={"label": "Statement"})
            st.dataframe(pivot, use_container_width=True, hide_index=True)

    with tab_knowledge:
        info_df = load_pp_info_perceptions()
        if info_df is None:
            st.info(
                "Data pending: run `export_pp_app_data.py`, upload "
                "`pp_info_perceptions.csv` to Drive, then paste its file ID into "
                "`data_loader.py`."
            )
        else:
            st.caption(
                "Fertility-return, FP-myth, and program-message knowledge items — "
                f"broken down by {view.lower()}. **These four questions were only "
                "asked in this Phone Pulse follow-up survey — there's no equivalent "
                "question in the Formative Research baseline, so this is descriptive "
                "only, not a baseline-vs-follow-up comparison.**"
            )
            info_sub = _filter_split(info_df, split_by)
            if info_sub.empty:
                st.info("No data available.")
            else:
                for question in QUESTION_CATEGORY_ORDER:
                    fig = _info_perception_chart(info_sub, question, order, colors)
                    if fig is None:
                        continue
                    st.plotly_chart(fig, use_container_width=True)
                    note = QUESTION_NOTES.get(question)
                    if note:
                        st.caption(note)
