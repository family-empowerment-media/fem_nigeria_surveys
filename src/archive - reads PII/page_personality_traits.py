import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from src.fem_colours import FEM_ORANGE, FEM_BROWN, FEM_TAUPE, FEM_STEEL, FEM_NAVY
from src.data_loader import load_personality_life_goals
from pipeline.agg_helpers import get_overall_series, get_split_series
# from src.data_loader import load_raw_data

# ── Choice label maps (from SurveyCTO schema) ─────────────────────────────────

LIFE_GOALS = {
    1:  "Enough food for children",
    2:  "Well-behaved children",
    3:  "Children go to school",
    4:  "Better education for myself",
    5:  "Good health for family",
    6:  "Better personal health",
    7:  "Living a long life",
    8:  "Looking good and fresh",
    9:  "More rest / less stress",
    10: "Good / supportive spouse",
    11: "Having more children",
    12: "Having fewer children",
    13: "Desire specific gender child",
    14: "Peaceful family",
    15: "Getting a job",
    16: "Stable income",
    17: "Better / respected work",
    18: "Starting a business",
    19: "Financial prosperity",
    20: "Building / owning a house",
    21: "Owning car or motorcycle",
    22: "More time for religion",
    23: "Visiting Mecca / religious goals",
    24: "Be responsible / wise / patient",
    25: "Respect from peers",
    26: "Helping others",
    27: "Living abroad",
    28: "Progress for the country",
    29: "Reversing past mistakes",
    -99: "Prefer not to say",
    -88: "Don't know",
    -22: "Other",
}

ROLE_MODELS = {
    1:  "Prophet",
    3:  "Religious leader",
    4:  "Women preachers",
    5:  "Traditional leader",
    7:  "Fervent religious believer",
    8:  "Spouse",
    9:  "Mother",
    10: "Father",
    11: "Brother",
    12: "Sister",
    13: "Friend",
    14: "Children",
    15: "Political leader",
    16: "Neighbour",
    17: "Colleague",
    18: "The elders",
    19: "Military officers",
    20: "Businessman",
    21: "Shopkeeper",
    22: "School teacher",
    23: "Health worker",
    24: "Superstar",
    25: "Successful people",
    26: "My boss",
    27: "Rich people",
    28: "Uncle",
    29: "Aunt",
    30: "Grandmother",
    31: "Grandfather",
    32: "A family relative",
    33: "Radio or TV character",
    34: "Nobody",
    -88: "Don't know",
    -99: "Prefer not to say",
    -22: "Other",
}

LIKEABLE_TRAITS = {
    1:  "Calm",
    2:  "Minds own business",
    3:  "Sociable",
    4:  "Kind",
    5:  "Not materialistic",
    6:  "No noise making",
    7:  "Patient",
    8:  "Endurance",
    9:  "Honest / Truthful",
    10: "Respectful",
    11: "Educated",
    13: "Forgives easily",
    14: "Disciplined",
    15: "Good believer",
    16: "Good behaviours",
    17: "Good lineage / social status",
    18: "Kind-hearted",
    19: "Good personality",
    20: "Helps people",
    21: "Respected",
    22: "Reliable",
    23: "Not a cheat",
    24: "Listens to people",
    25: "Religious",
    26: "Neat",
    27: "Cares about relatives",
    28: "Encourages good behaviour",
    29: "Brave",
    30: "Embraces everyone",
    31: "Has well-educated children",
    32: "Is rich",
    33: "Never complains",
    34: "Takes good care of family",
    -88: "Don't know",
    -99: "Prefer not to say",
    -22: "Other",
}

FORMING_BELIEFS = {
    1:  "Listen to my body and heart",
    2:  "Think about it alone",
    3:  "Look to religious texts",
    4:  "Seek opinions of knowledgeable people",
    5:  "Think about past experiences",
    6:  "See what is common around me",
    7:  "Try different options",
    8:  "Look at research",
    9:  "Don't know",
    10: "Prefer not to say",
    -22: "Other",
}

DECISION_CONFIDENT = {
    1:  "Husband",
    2:  "Friends",
    3:  "Radio",
    4:  "Sisters",
    5:  "In-laws",
    6:  "Mother",
    7:  "Father",
    8:  "Wife / Wives",
    9:  "Brothers",
    10: "Governmental authority",
    11: "Family relatives",
    12: "Neighbours",
    13: "Health workers",
    14: "Religious leaders (alive)",
    15: "Leaders",
    16: "Myself",
    17: "My children",
    18: "Religious leaders (texts)",
    19: "Media",
    20: "Co-wives",
    -99: "Prefer not to say",
    -88: "Don't know",
    -22: "Other",
}

LIKERT = {
    5: "Always",
    4: "Often",
    3: "Sometimes",
    2: "Rarely",
    1: "Almost never",
    0: "Never",
}

FEM_PALETTE = [FEM_ORANGE, FEM_BROWN, FEM_TAUPE, FEM_STEEL, FEM_NAVY]

WEIGHT_COL = "combined_weight_adjusted"

SPLIT_MAP = {
    "User group": "use",
    "Gender":     "gender",
    "Age group":  "age_group",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def weighted_counts(df, col, label_map=None, weight=WEIGHT_COL, exclude=(-88, -99, -22)):
    valid = df[[col, weight]].dropna()
    if exclude:
        valid = valid[~valid[col].isin(exclude)]
    totw = valid[weight].sum()
    if totw == 0:
        return pd.Series(dtype=float)
    result = valid.groupby(col)[weight].sum() / totw
    if label_map:
        result.index = result.index.map(lambda x: label_map.get(x, str(x)))
    return result.sort_values(ascending=False)


def weighted_multiselect_counts(df, col, label_map=None, weight=WEIGHT_COL, sep=" "):
    rows = []
    for _, row in df[[col, weight]].dropna().iterrows():
        vals = str(row[col]).split(sep)
        for v in vals:
            try:
                vint = int(v)
                if vint not in (-88, -99):
                    rows.append({"value": vint, weight: row[weight]})
            except ValueError:
                pass
    if not rows:
        return pd.Series(dtype=float)
    tmp = pd.DataFrame(rows)
    totw = df[weight].sum()
    result = tmp.groupby("value")[weight].sum() / totw
    if label_map:
        result.index = result.index.map(lambda x: label_map.get(x, str(x)))
    return result.sort_values(ascending=False)


def hbar(series, title, top_n=12, key=None):
    series = series.head(top_n)
    if series.empty:
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


def split_hbar(df, col, title, label_map=None, multi=False,
               split_col="use", top_n=10, key_prefix=""):
    groups = sorted(df[split_col].dropna().unique())
    traces = []
    for i, grp in enumerate(groups):
        sub = df[df[split_col] == grp]
        s = (weighted_multiselect_counts(sub, col, label_map)
             if multi else weighted_counts(sub, col, label_map))
        s = s.head(top_n)
        if s.empty:
            continue
        traces.append(go.Bar(
            name=str(grp),
            x=s.index.astype(str),
            y=s.values,
            marker_color=FEM_PALETTE[i % len(FEM_PALETTE)],
            text=[f"{v*100:.0f}%" for v in s.values],
            textposition="outside",
        ))
    if not traces:
        st.info("No data.")
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
    st.plotly_chart(fig, use_container_width=True,
                    key=f"{key_prefix}_{col}_{split_col}")


def likert_bar(df, col, title, label_map, key=None, split_col=None):
    """Stacked horizontal bar for Likert-scale responses, optionally split."""
    order = [5, 4, 3, 2, 1, 0]
    colors_likert = [FEM_ORANGE, FEM_BROWN, FEM_TAUPE, "#a0a0a0", FEM_STEEL, FEM_NAVY]

    if split_col:
        groups = sorted(df[split_col].dropna().unique())
        y_labels = [str(g) for g in groups]
        traces = []
        for lvl, col_hex in zip(order, colors_likert):
            x_vals = []
            for grp in groups:
                sub = df[df[split_col] == grp]
                valid = sub[[col, WEIGHT_COL]].dropna()
                totw = valid[WEIGHT_COL].sum()
                w = valid.loc[valid[col] == lvl, WEIGHT_COL].sum()
                x_vals.append(w / totw * 100 if totw > 0 else 0)
            traces.append(go.Bar(
                name=label_map.get(lvl, str(lvl)),
                y=y_labels, x=x_vals,
                orientation="h",
                marker_color=col_hex,
                text=[f"{v:.0f}%" if v >= 5 else "" for v in x_vals],
                textposition="inside",
            ))
    else:
        y_labels = ["All respondents"]
        traces = []
        valid = df[[col, WEIGHT_COL]].dropna()
        totw = valid[WEIGHT_COL].sum()
        for lvl, col_hex in zip(order, colors_likert):
            w = valid.loc[valid[col] == lvl, WEIGHT_COL].sum()
            pct = w / totw * 100 if totw > 0 else 0
            traces.append(go.Bar(
                name=label_map.get(lvl, str(lvl)),
                y=y_labels, x=[pct],
                orientation="h",
                marker_color=col_hex,
                text=[f"{pct:.0f}%" if pct >= 5 else ""],
                textposition="inside",
            ))

    fig = go.Figure(traces)
    fig.update_layout(
        title=title,
        barmode="stack",
        xaxis=dict(range=[0, 100], ticksuffix="%", showgrid=False),
        yaxis=dict(showgrid=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=40, b=10, l=10, r=10),
        height=max(180, len(y_labels) * 52 + 80),
        legend=dict(orientation="h", yanchor="bottom", y=-0.35),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


# ── Section renderers ─────────────────────────────────────────────────────────

def render_life_goals(df, split_col):
    st.subheader("Life goals")
    st.caption("Top 3 things respondents would most like to change in their lives.")

    col1, col2 = st.columns([3, 2])
    with col1:
        if "life_goals" in df.columns:
            s = weighted_multiselect_counts(df, "life_goals", LIFE_GOALS)
            hbar(s, "Top life goals (% mentioning)", top_n=12, key="pg_goals")
    with col2:
        if "life_goals_main" in df.columns:
            s2 = weighted_counts(df, "life_goals_main", LIFE_GOALS)
            hbar(s2, "Single most important goal", top_n=8, key="pg_goals_main")

    with st.expander("Goals split by demographic"):
        tab1, tab2 = st.tabs(["Top 3 goals", "Most important goal"])
        with tab1:
            if "life_goals" in df.columns:
                split_hbar(df, "life_goals", "", LIFE_GOALS,
                           multi=True, split_col=split_col, top_n=8, key_prefix="pgs")
        with tab2:
            if "life_goals_main" in df.columns:
                split_hbar(df, "life_goals_main", "", LIFE_GOALS,
                           split_col=split_col, top_n=8, key_prefix="pgm")

    # Achievability
    if "life_goals_achievable" in df.columns:
        st.markdown("**Can goals be achieved through family planning?**")
        s3 = weighted_counts(df, "life_goals_achievable", {1: "Yes", 0: "No", -88: "Don't know"})
        hbar(s3, "", top_n=4, key="pg_achievable")


def render_role_models(df, split_col):
    st.subheader("Role models")
    st.caption("Who do respondents look up to?")

    col1, col2 = st.columns(2)
    with col1:
        if "role_models" in df.columns:
            s = weighted_multiselect_counts(df, "role_models", ROLE_MODELS)
            hbar(s, "Role models (% mentioning)", top_n=12, key="pg_rm")
    with col2:
        if "likeable_traits" in df.columns:
            s2 = weighted_multiselect_counts(df, "likeable_traits", LIKEABLE_TRAITS)
            hbar(s2, "Why do they look up to them?", top_n=12, key="pg_traits")

    with st.expander("Role models split by demographic"):
        if "role_models" in df.columns:
            split_hbar(df, "role_models", "", ROLE_MODELS,
                       multi=True, split_col=split_col, top_n=8, key_prefix="pgrs")


def render_health_beliefs(df, split_col):
    st.subheader("Health belief formation")
    st.caption("How do respondents form beliefs about health topics?")

    if "forming_beliefs" in df.columns:
        s = weighted_multiselect_counts(df, "forming_beliefs", FORMING_BELIEFS)
        hbar(s, "How beliefs are formed (% mentioning)", key="pg_beliefs")

        with st.expander("Split by demographic"):
            split_hbar(df, "forming_beliefs", "", FORMING_BELIEFS,
                       multi=True, split_col=split_col, top_n=8, key_prefix="pgbs")

    st.markdown("**Most trusted person for difficult health decisions**")
    if "decision_confident" in df.columns:
        col1, col2 = st.columns(2)
        with col1:
            s2 = weighted_counts(df, "decision_confident", DECISION_CONFIDENT)
            hbar(s2, "Single most trusted person", top_n=10, key="pg_trust1")
        with col2:
            if "decision_confident_3" in df.columns:
                s3 = weighted_multiselect_counts(df, "decision_confident_3", DECISION_CONFIDENT)
                hbar(s3, "Top 3 trusted people", top_n=10, key="pg_trust3")


def render_wellbeing(df, split_col):
    st.subheader("Wellbeing")
    st.caption("Self-reported happiness and life satisfaction.")

    col1, col2 = st.columns(2)
    with col1:
        if "happiness" in df.columns:
            likert_bar(df, "happiness",
                       "How often do you feel joy in daily life?",
                       LIKERT, key="pg_happy",
                       split_col=split_col if split_col != "use" else None)
    with col2:
        if "satisfaction" in df.columns:
            likert_bar(df, "satisfaction",
                       "How often do you feel satisfied with life overall?",
                       LIKERT, key="pg_satisfy",
                       split_col=split_col if split_col != "use" else None)


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    st.title("Personality & Influencers")

    # df = load_raw_data()
    df = load_personality_life_goals()
    s = get_overall_series(df)                    # for overall chart

    split_by  = st.radio("Split all charts by", list(SPLIT_MAP.keys()), horizontal=True)
    split_col = SPLIT_MAP[split_by]
    # pivot = get_split_series(df, split_col)  


    st.divider()
    render_life_goals(df, split_col)
    st.divider()
    render_role_models(df, split_col)
    st.divider()
    render_health_beliefs(df, split_col)
    st.divider()
    render_wellbeing(df, split_col)
