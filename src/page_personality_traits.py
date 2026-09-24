import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.fem_colours import FEM_PALETTE
from src.data_loader import (
    load_personality_life_goals,
    load_personality_goals_achievable,
    load_personality_role_models,
    load_personality_likeable_traits,
    load_personality_forming_beliefs,
    load_personality_decision_confident,
    load_personality_wellbeing,
)

SPLIT_MAP = {
    "User group": "use",
    "Gender":     "gender",
    "Age group":  "age_group",
}

_MISSING = (
    "Pre-aggregated data not found. "
    "Run `python -m pipeline.run_pipeline --pages personality` (from pipeline_output/) to generate it."
)


# ── Chart helpers ─────────────────────────────────────────────────────────────

def _hbar(series, title, top_n=12, key=None):
    series = series.head(top_n)
    if series is None or series.empty:
        return
    colors = (FEM_PALETTE * (len(series) // len(FEM_PALETTE) + 1))[:len(series)]
    fig = go.Figure(go.Bar(
        y=series.index.astype(str),
        x=series.values,
        orientation="h",
        marker_color=colors,
        text=[f"{v*100:.1f}%" for v in series.values],
        textposition="outside",
        cliponaxis=False,
    ))
    fig.update_layout(
        title=title,
        xaxis=dict(showgrid=False, showticklabels=False,
                   range=[0, series.max() * 1.35] if len(series) else [0, 1]),
        yaxis=dict(showgrid=False, autorange="reversed"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=80, t=36, b=10),
        height=max(200, len(series) * 34 + 60),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def _grouped_bar(df_long, split_col, label_col, value_col, title,
                 top_n=10, key=None):
    if df_long is None or df_long.empty:
        return
    sub = df_long[df_long["split"] == split_col]
    if sub.empty:
        st.info("No data for this split.")
        return

    top_labels = (
        sub.groupby(label_col)[value_col].max()
        .nlargest(top_n).index.tolist()
    )
    sub = sub[sub[label_col].isin(top_labels)]
    groups = sorted(sub["group"].unique())

    traces = []
    for i, grp in enumerate(groups):
        gdf = sub[sub["group"] == grp].set_index(label_col)[value_col]
        traces.append(go.Bar(
            name=str(grp),
            x=gdf.index.astype(str),
            y=gdf.values,
            marker_color=FEM_PALETTE[i % len(FEM_PALETTE)],
            text=[f"{v*100:.0f}%" for v in gdf.values],
            textposition="outside",
        ))
    if not traces:
        return
    fig = go.Figure(traces)
    fig.update_layout(
        title=title,
        barmode="group",
        yaxis=dict(tickformat=".0%", showgrid=False, title="% of respondents"),
        xaxis=dict(showgrid=False, tickangle=-30),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=40, b=80, l=10, r=10),
        height=380,
        legend_title=split_col,
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def _overall_series(df_long, label_col="label", value_col="proportion", question=None):
    if df_long is None or df_long.empty:
        return pd.Series(dtype=float)
    mask = (df_long["split"] == "none") & (df_long["group"] == "all")
    if question and "question" in df_long.columns:
        mask &= df_long["question"] == question
    return df_long[mask].set_index(label_col)[value_col].sort_values(ascending=False)


# ── Section renderers ─────────────────────────────────────────────────────────

def render_life_goals(df_goals, df_achievable, split_col):
    st.subheader("Life goals")
    st.caption("Top 3 things respondents would most like to change in their lives.")

    if df_goals is None:
        st.warning(_MISSING)
        return

    col1, col2 = st.columns([3, 2])
    with col1:
        sub = df_goals[df_goals.get("question", pd.Series("top3", index=df_goals.index)) == "top3"] \
              if "question" in df_goals.columns else df_goals
        _hbar(_overall_series(sub), "Top life goals (% mentioning)", top_n=12,
              key="pg_goals")
    with col2:
        if "question" in df_goals.columns:
            _hbar(_overall_series(df_goals, question="main"),
                  "Single most important goal", top_n=8, key="pg_goals_main")

    with st.expander("Goals split by demographic"):
        tab1, tab2 = st.tabs(["Top 3 goals", "Most important goal"])
        with tab1:
            sub3 = df_goals[df_goals["question"] == "top3"] \
                   if "question" in df_goals.columns else df_goals
            _grouped_bar(sub3, split_col, "label", "proportion", "",
                         top_n=8, key=f"pgs_{split_col}")
        with tab2:
            if "question" in df_goals.columns:
                subm = df_goals[df_goals["question"] == "main"]
                _grouped_bar(subm, split_col, "label", "proportion", "",
                             top_n=8, key=f"pgm_{split_col}")

    if df_achievable is not None:
        st.markdown("**Can goals be achieved through family planning?**")
        _hbar(_overall_series(df_achievable), "", top_n=4, key="pg_achievable")


def render_role_models(df_models, df_traits, split_col):
    st.subheader("Role models")
    st.caption("Who do respondents look up to?")

    col1, col2 = st.columns(2)
    with col1:
        if df_models is not None:
            _hbar(_overall_series(df_models), "Role models (% mentioning)",
                  top_n=12, key="pg_rm")
    with col2:
        if df_traits is not None:
            _hbar(_overall_series(df_traits), "Why do they look up to them?",
                  top_n=12, key="pg_traits")

    if df_models is not None:
        with st.expander("Role models split by demographic"):
            _grouped_bar(df_models, split_col, "label", "proportion", "",
                         top_n=8, key=f"pgrs_{split_col}")


def render_health_beliefs(df_beliefs, df_confident, split_col):
    st.subheader("Health belief formation")
    st.caption("How do respondents form beliefs about health topics? "
                "(Redesigned for Benin's survey -- see FORMING_BELIEFS in pipeline_output/pipeline/config.py.)")

    if df_beliefs is not None:
        _hbar(_overall_series(df_beliefs),
              "How beliefs are formed (% mentioning)", key="pg_beliefs")
        with st.expander("Split by demographic"):
            _grouped_bar(df_beliefs, split_col, "label", "proportion", "",
                         top_n=8, key=f"pgbs_{split_col}")

    st.markdown("**Most trusted person for difficult health decisions**")
    if df_confident is not None:
        col1, col2 = st.columns(2)
        with col1:
            sub_single = df_confident[df_confident["question"] == "single"] \
                         if "question" in df_confident.columns else df_confident
            _hbar(_overall_series(sub_single), "Single most trusted person",
                  top_n=10, key="pg_trust1")
        with col2:
            if "question" in df_confident.columns:
                sub3 = df_confident[df_confident["question"] == "top3"]
                _hbar(_overall_series(sub3), "Top 3 trusted people",
                      top_n=10, key="pg_trust3")


def render_wellbeing(df_wellbeing, split_col):
    st.subheader("Wellbeing")
    st.caption("Self-reported joy and life satisfaction.")

    if df_wellbeing is None:
        st.warning(_MISSING)
        return

    # NOTE: Niger's version rendered this as a 6-category Likert stacked bar
    # ("Always" .. "Never"). Benin's happiness/satisfaction questions are an
    # open numeric rating scale (raw values are digit strings, not a fixed
    # set of Likert phrases -- see LIKERT in pipeline_output/pipeline/config.py,
    # which doesn't match this data at all), so that chart type doesn't apply
    # here. Showing the raw value distribution instead.
    for tag, title in [("happiness", "How often do you feel joy in daily life?"),
                        ("satisfaction", "How often do you feel satisfied with life overall?")]:
        sub = df_wellbeing[df_wellbeing["question"] == tag] \
              if "question" in df_wellbeing.columns else df_wellbeing
        overall = _overall_series(sub)
        # Sort numerically where possible, non-numeric responses (e.g. "don't know") last
        overall = overall.reindex(
            sorted(overall.index, key=lambda x: (not str(x).replace('.', '', 1).isdigit(),
                                                   float(x) if str(x).replace('.', '', 1).isdigit() else 0))
        )
        _hbar(overall, title, top_n=20, key=f"pg_wellbeing_{tag}")
        with st.expander(f"{title} — split by demographic"):
            _grouped_bar(sub, split_col, "label", "proportion", "",
                         top_n=20, key=f"pgw_{tag}_{split_col}")


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    st.title("Personality & Influencers")

    df_goals      = load_personality_life_goals()
    df_achievable = load_personality_goals_achievable()
    df_models     = load_personality_role_models()
    df_traits     = load_personality_likeable_traits()
    df_beliefs    = load_personality_forming_beliefs()
    df_confident  = load_personality_decision_confident()
    df_wellbeing  = load_personality_wellbeing()

    split_by  = st.radio("Split all charts by", list(SPLIT_MAP.keys()), horizontal=True)
    split_col = SPLIT_MAP[split_by]

    st.divider()
    render_life_goals(df_goals, df_achievable, split_col)
    st.divider()
    render_role_models(df_models, df_traits, split_col)
    st.divider()
    render_health_beliefs(df_beliefs, df_confident, split_col)
    st.divider()
    render_wellbeing(df_wellbeing, split_col)
