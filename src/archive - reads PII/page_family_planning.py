import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from src.fem_colours import FEM_ORANGE, FEM_BROWN, FEM_TAUPE, FEM_STEEL, FEM_NAVY
from src.data_loader import load_raw_data

# ── Choice label maps (from SurveyCTO schema) ─────────────────────────────────

TIME_TO_PREGNANT = {
    1: "Within 6 months",
    2: "6–12 months",
    3: "1–2 years",
    4: "More than 2 years",
    5: "Already pregnant",
    6: "No more children",
    -88: "Don't know",
    -99: "Prefer not to say",
}

CONTRACEPTIVE_METHODS = {
    1:  "Sterilisation",
    2:  "Implants",
    3:  "Oral contraceptive pills",
    4:  "IUD",
    5:  "Injectables",
    6:  "Condoms",
    7:  "Vaginal ring",
    8:  "Contraceptive patch",
    9:  "Vaginal barrier methods",
    10: "Withdrawal",
    11: "Abstinence",
    12: "Calendar / Rhythm",
    13: "Standard Days Method",
    14: "Lactational Amenorrhea",
    15: "Emergency contraception",
    0:  "None",
    -88: "Don't know",
    -99: "Prefer not to say",
    -22: "Other",
}

REASON_USE = {
    1:  "Space births",
    2:  "No more children",
    -88: "Don't know",
    -99: "Prefer not to say",
    -22: "Other",
}

YESNO = {1: "Yes", 0: "No", -88: "Don't know", -99: "Prefer not to say"}

FEM_PALETTE = [FEM_ORANGE, FEM_BROWN, FEM_TAUPE, FEM_STEEL, FEM_NAVY]

WEIGHT_COL = "combined_weight_adjusted"

SPLIT_MAP = {
    "User group": "use",
    "Gender":     "gender",
    "Age group":  "age_group",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def weighted_counts(df, col, label_map=None, weight=WEIGHT_COL, exclude=(-88, -99, -22)):
    """Weighted value counts for a single-select column, returning proportions."""
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
    """
    Weighted counts for a select_multiple column stored as space-separated values.
    Returns proportions relative to number of respondents (not responses).
    """
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


def hbar(series, title, pct=True, height=None, key=None):
    if series.empty:
        return
    colors = (FEM_PALETTE * (len(series) // len(FEM_PALETTE) + 1))[:len(series)]
    vals = series.values
    text = [f"{v*100:.1f}%" if pct else f"{v:.1f}" for v in vals]
    fig = go.Figure(go.Bar(
        y=series.index.astype(str),
        x=vals,
        orientation="h",
        marker_color=colors,
        text=text,
        textposition="outside",
        cliponaxis=False,
    ))
    fig.update_layout(
        title=title,
        xaxis=dict(
            showgrid=False, showticklabels=False,
            range=[0, max(vals) * 1.35] if len(vals) else [0, 1],
        ),
        yaxis=dict(showgrid=False, autorange="reversed"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=80, t=36, b=10),
        height=height or max(180, len(series) * 36 + 60),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def split_bar(df, col, title, label_map=None, multi=False, split_col="use",
              top_n=8, key_prefix=""):
    """Grouped bar chart split by a demographic column."""
    groups = sorted(df[split_col].dropna().unique())
    traces = []
    for i, grp in enumerate(groups):
        sub = df[df[split_col] == grp]
        if multi:
            s = weighted_multiselect_counts(sub, col, label_map)
        else:
            s = weighted_counts(sub, col, label_map)
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
        st.info("No data for this split.")
        return
    fig = go.Figure(traces)
    fig.update_layout(
        title=title,
        barmode="group",
        yaxis=dict(tickformat=".0%", showgrid=False, title="% of respondents"),
        xaxis=dict(showgrid=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=40, b=60, l=10, r=10),
        height=360,
        legend_title=split_col,
    )
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_{col}_{split_col}")


# ── Funnel: awareness -> ever used -> currently using ─────────────────────────

def render_funnel(df, split_col):
    st.markdown("**Contraceptive use funnel**")
    groups = ["All"] + sorted(df[split_col].dropna().unique().tolist())
    selected_grp = st.selectbox("Filter group", groups, key="fp_funnel_grp")
    sub = df if selected_grp == "All" else df[df[split_col] == selected_grp]

    w = sub[WEIGHT_COL].sum()
    if w == 0:
        st.info("No data.")
        return

    def wprop(mask):
        return (sub.loc[mask, WEIGHT_COL].sum() / w) * 100

    # Aware of any method
    aware_mask = sub["birth_spacing"].isin([1]) if "birth_spacing" in sub.columns else (sub.index == -1)
    # Ever used
    ever_mask  = sub["ever_use"].isin([1]) if "ever_use" in sub.columns else (sub.index == -1)
    # Current user
    curr_mask  = sub["current_use"].isin([1]) if "current_use" in sub.columns else (sub.index == -1)

    stages = ["Aware of methods", "Ever used", "Currently using"]
    values = [wprop(aware_mask), wprop(ever_mask), wprop(curr_mask)]

    fig = go.Figure(go.Funnel(
        y=stages,
        x=values,
        textinfo="value+percent initial",
        texttemplate="%{value:.1f}%",
        marker_color=[FEM_ORANGE, FEM_BROWN, FEM_NAVY],
        connector=dict(line=dict(color=FEM_TAUPE, width=2)),
    ))
    fig.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, key="fp_funnel")


# ── Section renderers ─────────────────────────────────────────────────────────

def render_awareness_use(df, split_col):
    st.subheader("Awareness & use")

    col1, col2 = st.columns(2)
    with col1:
        render_funnel(df, split_col)
    with col2:
        st.markdown("**Preferred timing of next pregnancy**")
        s = weighted_counts(df, "time_before_preferred_pregnancy", TIME_TO_PREGNANT)
        hbar(s, "", key="fp_timing")

    st.markdown("**Reason for current/recent use**")
    split_bar(df, "reason_current_use", "", REASON_USE, split_col=split_col, key_prefix="fp_reason")


def render_methods(df, split_col):
    st.subheader("Methods known vs. ever used vs. currently using")

    col1, col2, col3 = st.columns(3)
    for col_obj, col_name, title, key in [
        (col1, "known_contraceptive_options", "Methods known", "fp_known"),
        (col2, "ever_used_methods",           "Ever used",     "fp_ever"),
        (col3, "current_use_methods",         "Currently using", "fp_curr"),
    ]:
        if col_name in df.columns:
            with col_obj:
                s = weighted_multiselect_counts(df, col_name, CONTRACEPTIVE_METHODS).head(10)
                hbar(s, title, key=key)

    st.markdown("**Methods by split**")
    tab1, tab2, tab3 = st.tabs(["Known", "Ever used", "Current"])
    for tab, col_name, kpfx in [
        (tab1, "known_contraceptive_options", "fpsk"),
        (tab2, "ever_used_methods",           "fpse"),
        (tab3, "current_use_methods",         "fpsc"),
    ]:
        with tab:
            if col_name in df.columns:
                split_bar(df, col_name, "", CONTRACEPTIVE_METHODS,
                          multi=True, split_col=split_col, top_n=8, key_prefix=kpfx)


def render_intent(df, split_col):
    st.subheader("Future intent & non-use reasons")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Intends to use contraception in future**")
        if "future_intent" in df.columns:
            s = weighted_counts(df, "future_intent", YESNO)
            hbar(s, "", key="fp_intent")

    with col2:
        st.markdown("**Considered use (non-users)**")
        if "considered_use" in df.columns:
            s = weighted_counts(df, "considered_use", YESNO)
            hbar(s, "", key="fp_considered")

    # Free text: reasons for non-use
    if "reason_current_nonuse" in df.columns:
        with st.expander("Reasons for non-use (free text sample)"):
            sample = (
                df[df["reason_current_nonuse"].notna()]["reason_current_nonuse"]
                .value_counts()
                .head(15)
                .reset_index()
            )
            sample.columns = ["Reason", "Count"]
            st.dataframe(sample, use_container_width=True, hide_index=True)


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    st.title("Family Planning")

    df = load_raw_data()

    split_by  = st.radio("Split all charts by", list(SPLIT_MAP.keys()), horizontal=True)
    split_col = SPLIT_MAP[split_by]

    st.divider()
    render_awareness_use(df, split_col)
    st.divider()
    render_methods(df, split_col)
    st.divider()
    render_intent(df, split_col)
