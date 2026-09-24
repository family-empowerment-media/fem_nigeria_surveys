"""
page_respondents.py — Respondent Profile
Descriptive statistics of the survey sample.
All data is pre-aggregated (no PII).
"""

import streamlit as st
import pandas as pd
from src.data_loader import load_respondents_profile
from src.translations import tr

# Display order of variables and their labels
VAR_ORDER = [
    ("use",             "FP use group"),
    ("gender",          "Gender"),
    ("age_group",       "Age group"),
    ("occupation",      "Occupation"),
    ("religion",        "Religion"),
    ("urban_rural", "Settlement type"),
    ("region",          "Region"),
    ("province",        "Province"),
]

# Preferred category order within variables (others appended alphabetically)
CATEGORY_ORDER = {
    "use":       ["Current user", "Past user", "Future user", "Non-user"],
    "age_group": ["16-20", "21-30", "31-45"],
    "gender":    ["Femme", "Homme"],
    # North-East = Borgou, North-West = Donga, South-South = Littoral/Ouémé/Atlantique,
    # Mid-South = Couffo/Zou/Plateau (per user-supplied mapping, 2026-08-24)
    "region":    ["North-East", "North-West", "South-South", "Mid-South"],
}

_MISSING = (
    "Respondent profile data not found. "
    "Run `python -m pipeline.run_pipeline --pages respondents` (from pipeline_output/) to generate it."
)


def _build_table(df):
    rows = []
    for var, label in VAR_ORDER:
        sub = df[df["variable"] == var].copy()
        if sub.empty:
            continue

        # Apply preferred category order
        if var in CATEGORY_ORDER:
            ordered = [c for c in CATEGORY_ORDER[var] if c in sub["category"].values]
            rest    = sorted(c for c in sub["category"].values if c not in ordered)
            sub = sub.set_index("category").reindex(ordered + rest).reset_index()
        else:
            sub = sub.sort_values("count", ascending=False)

        for _, row in sub.iterrows():
            rows.append({
                "Variable":  label,
                "Category":  tr(row["category"]),
                "N":         int(row["count"]),
                "%":         f"{row['proportion'] * 100:.1f}%",
            })

    return pd.DataFrame(rows)


def render():
    st.markdown("## Respondent Profile")

    df = load_respondents_profile()
    if df is None:
        st.warning(_MISSING)
        return

    # Headline N
    total_row = df[df["variable"] == "_total"]
    if not total_row.empty:
        n = int(total_row["count"].iloc[0])
        st.metric("Survey respondents (N)", f"{n:,}")

    st.markdown("")

    table = _build_table(df)
    if table.empty:
        st.info("No demographic data available.")
        return

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Variable": st.column_config.TextColumn("Variable", width="medium"),
            "Category": st.column_config.TextColumn("Category", width="medium"),
            "N":        st.column_config.NumberColumn("N", format="%d", width="small"),
            "%":        st.column_config.TextColumn("%", width="small"),
        },
    )
