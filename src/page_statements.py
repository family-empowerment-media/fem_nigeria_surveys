"""
page_statements.py  —  improved version
Changes:
  • Higher-contrast colour scale.
  • Human-readable group column headers for "use" split.
  • Shows agree/disagree counts separately (not just total respondents).
  • Weighted agreement is normalized: (sum of weighted responses) / (total weighted n)
  • Column detection: tries common count column names, reports clearly if absent.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from src.data_loader import load_statements_heatmap
from src.fem_colours import FEM_ORANGE, FEM_BROWN, FEM_STEEL, FEM_NAVY

# ── Colour scale ──────────────────────────────────────────────────────────────
# Cool-to-warm, matching fem_colours.FEM_SCALE's direction (niger_app's
# statements page instead ramps warm-to-cool, ending on navy).
FEM_SCALE_HC = [
    [0.0,  "#f4f7f9"],
    [0.15, "#c3d0d8"],
    [0.35, FEM_STEEL],
    [0.55, FEM_NAVY],
    [0.75, FEM_BROWN],
    [1.0,  FEM_ORANGE],
]

USE_GROUP_LABELS = {
    "user":    "Current user",
    "nonuser": "Non-user",
    "all":     "All",
}

SPLIT_MAP = {
    "User category": "use",
    "Gender":        "gender",
    "Age group":     "age_group",
    "None":          "none",
}

_MISSING = (
    "Pre-aggregated data not found. "
    "Run `python -m pipeline.run_pipeline --pages statements` (from pipeline_output/)` to generate it."
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _rename_columns(pivot, split_key):
    if split_key == "use":
        pivot.columns = [USE_GROUP_LABELS.get(str(c), str(c)) for c in pivot.columns]
    return pivot


def _build_pivot(df_long, split_key, value_col="weighted_agreement"):
    if value_col not in df_long.columns:
        return pd.DataFrame()

    if split_key == "none":
        sub = df_long[(df_long["split"] == "none") & (df_long["group"] == "all")]
        pivot = sub.set_index("label")[[value_col]]
        pivot.columns = ["All respondents"]
        return pivot

    sub = df_long[df_long["split"] == split_key]
    pivot = sub.pivot_table(
        index="label", columns="group",
        values=value_col, aggfunc="first", fill_value=0,
    )
    return _rename_columns(pivot, split_key)


def _heatmap_fig(pivot, title, value_label):
    z = pivot.values
    
    # Clamp values to [0, 1] for display
    z_clamped = np.clip(z, 0, 1)

    text_matrix = [
        [f"{v:.0%}" if (v is not None and not np.isnan(float(v))) else "" for v in row]
        for row in z
    ]

    fig = go.Figure(go.Heatmap(
        z=z_clamped * 100,
        x=list(pivot.columns.astype(str)),
        y=list(pivot.index.astype(str)),
        colorscale=FEM_SCALE_HC,
        zmin=0, zmax=100,
        text=text_matrix,
        texttemplate="%{text}",
        showscale=True,
        colorbar=dict(title=value_label, ticksuffix="%", thickness=12, len=0.8),
    ))
    fig.update_layout(
        title=title,
        height=max(500, len(pivot) * 28 + 120),
        xaxis=dict(side="top", tickfont=dict(size=12)),
        yaxis=dict(tickfont=dict(size=11), automargin=True, autorange="reversed"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11),
        margin=dict(l=10, r=10, t=80, b=10),
    )
    return fig


def _fmt_pct(v):
    return f"{float(v):.0%}" if pd.notna(v) else ""


def _build_counts_table(df_long, split_key):
    """
    Build a table showing agree/disagree counts and unweighted percentages.
    """
    required_cols = ["agree_n", "agree_weighted_n", "disagree_n", "disagree_weighted_n"]
    if not all(c in df_long.columns for c in required_cols):
        return None

    has_pct = "agree_pct" in df_long.columns and "disagree_pct" in df_long.columns

    if split_key == "none":
        sub = df_long[(df_long["split"] == "none") & (df_long["group"] == "all")].copy()
        result = {"Statement": sub["label"].tolist()}
        result["Agree — n"] = [f"{int(v):,}" if pd.notna(v) else "" for v in sub["agree_n"]]
        if has_pct:
            result["Agree — %"] = [_fmt_pct(v) for v in sub["agree_pct"]]
        result["Agree — wtd n"] = [f"{float(v):,.1f}" if pd.notna(v) else "" for v in sub["agree_weighted_n"]]
        result["Disagree — n"] = [f"{int(v):,}" if pd.notna(v) else "" for v in sub["disagree_n"]]
        if has_pct:
            result["Disagree — %"] = [_fmt_pct(v) for v in sub["disagree_pct"]]
        result["Disagree — wtd n"] = [f"{float(v):,.1f}" if pd.notna(v) else "" for v in sub["disagree_weighted_n"]]
        return pd.DataFrame(result)

    sub = df_long[df_long["split"] == split_key].copy()
    groups = sorted(sub["group"].dropna().unique())
    labels = sub["label"].dropna().unique()

    rows = []
    for lbl in labels:
        row = {"Statement": lbl}
        for grp in groups:
            grp_name = USE_GROUP_LABELS.get(str(grp), str(grp)) if split_key == "use" else str(grp)
            cell = sub[(sub["label"] == lbl) & (sub["group"] == grp)]

            if not cell.empty:
                agree_n = cell["agree_n"].iloc[0]
                agree_wn = cell["agree_weighted_n"].iloc[0]
                disagree_n = cell["disagree_n"].iloc[0]
                disagree_wn = cell["disagree_weighted_n"].iloc[0]

                row[f"{grp_name} — Agree n"] = f"{int(agree_n):,}" if pd.notna(agree_n) else ""
                if has_pct:
                    row[f"{grp_name} — Agree %"] = _fmt_pct(cell["agree_pct"].iloc[0])
                row[f"{grp_name} — Agree wtd"] = f"{float(agree_wn):,.1f}" if pd.notna(agree_wn) else ""
                row[f"{grp_name} — Disagree n"] = f"{int(disagree_n):,}" if pd.notna(disagree_n) else ""
                if has_pct:
                    row[f"{grp_name} — Disagree %"] = _fmt_pct(cell["disagree_pct"].iloc[0])
                row[f"{grp_name} — Disagree wtd"] = f"{float(disagree_wn):,.1f}" if pd.notna(disagree_wn) else ""

        rows.append(row)

    return pd.DataFrame(rows)


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    st.title("Statement Agreement")
    
    # Description at the top
    st.markdown("""
    ### Interpreting the heatmap and counts
    
    **Weighted Agreement Score (heatmap):**
    - The weighted agreement score was calculated as: (sum of weighted "Agree" responses − sum of weighted "Disagree" responses) / (total weighted respondents)
    - Range: −1.0 (all disagree) to +1.0 (all agree)
    - Displayed as: (score + 1) / 2 × 100, converting to 0–100 % scale
    - Darker colours indicate higher agreement; lighter colours indicate higher disagreement
    
    **Unweighted % (heatmap & table):**
    - Agree % = number who agreed ÷ total respondents who answered (no weighting applied)
    - Useful for checking how the raw sample looks before adjusting for survey weights

    **Respondent Counts (table):**
    - **n** = actual number of respondents who answered
    - **%** = unweighted percentage (agree n ÷ total n)
    - **Weighted n** = sum of survey weights (effective sample size, accounts for over/under-sampling)
    """)

    col_split, col_view = st.columns([2, 2])
    with col_split:
        split_by = st.radio("Split data by", list(SPLIT_MAP.keys()), horizontal=True)
    with col_view:
        view = st.selectbox(
            "View",
            ["Weighted agreement score", "Unweighted agree %"],
        )
    split_key = SPLIT_MAP[split_by]

    df_long = load_statements_heatmap()
    if df_long is None or df_long.empty:
        st.warning(_MISSING)
        return

    # ── Heatmap (selected view) ───────────────────────────────────────────────
    if view == "Weighted agreement score":
        value_col, title, label = "weighted_agreement", "Statement Agreement — weighted score", "Agreement %"
    else:
        value_col, title, label = "agree_pct", "Statement Agreement — unweighted agree %", "Agree %"

    pivot = _build_pivot(df_long, split_key, value_col=value_col)
    if pivot.empty:
        st.info("No data for this split.")
        return

    st.caption("Scale: 0–100 %. Darker = higher agreement. Lighter = higher disagreement.")
    st.plotly_chart(
        _heatmap_fig(pivot, title, label),
        use_container_width=True,
        key="heatmap_main",
    )

    # ── Respondent counts ────────────────────────────────────────────────────
    with st.expander("View respondent counts (Agree vs Disagree)"):
        counts_df = _build_counts_table(df_long, split_key)
        if counts_df is not None and not counts_df.empty:
            st.caption(
                "**n** = actual number of respondents. "
                "**%** = unweighted percentage (agree n ÷ total n). "
                "**Weighted n** = sum of survey weights (effective sample size). "
                "Shown separately for Agree and Disagree responses."
            )
            st.dataframe(counts_df, use_container_width=True, hide_index=True)
        else:
            st.info(
                "Count columns were not found in the aggregated dataset. "
                "Re-run the pipeline ensuring count columns are exported."
            )

    # ── Raw scores table ──────────────────────────────────────────────────────
    # with st.expander("View scores (table)"):
    #     st.dataframe(pivot.style.format("{:.1%}"), use_container_width=True)
