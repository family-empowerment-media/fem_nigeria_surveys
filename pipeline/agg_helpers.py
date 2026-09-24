"""
Shared rendering helpers for pages that use pre-aggregated pipeline CSVs.

Each page receives long-format DataFrames with columns:
  label / method / response  — the category label
  split                      — which split dimension ("use", "gender", "age_group", "none")
  group                      — the group within that split ("user", "male", "16-20", "all")
  proportion                 — weighted proportion (0-1)

These helpers extract a Series or DataFrame for the right split/group
and pass it to the existing plotting functions unchanged.
"""

import pandas as pd


def get_split_series(df_long, split_col, label_col="label", value_col="proportion"):
    """
    From a long-format aggregated DataFrame, return a wide pivot:
      index = label, columns = groups within split_col.
    For 'none' split, returns a Series (single column).
    """
    if df_long is None or df_long.empty:
        return pd.Series(dtype=float)

    if split_col == "none" or split_col == "":
        sub = df_long[df_long["split"] == "none"]
        return sub.set_index(label_col)[value_col].sort_values(ascending=False)

    sub = df_long[df_long["split"] == split_col]
    if sub.empty:
        return pd.DataFrame()

    pivot = sub.pivot_table(index=label_col, columns="group",
                            values=value_col, aggfunc="first")
    return pivot


def get_overall_series(df_long, label_col="label", value_col="proportion"):
    """Return overall (no split) proportions as a Series."""
    if df_long is None or df_long.empty:
        return pd.Series(dtype=float)
    sub = df_long[(df_long["split"] == "none") & (df_long["group"] == "all")]
    return sub.set_index(label_col)[value_col].sort_values(ascending=False)


def get_split_for_group(df_long, split_col, group_val,
                        label_col="label", value_col="proportion"):
    """Return proportions for a single group within a split."""
    if df_long is None or df_long.empty:
        return pd.Series(dtype=float)
    sub = df_long[(df_long["split"] == split_col) & (df_long["group"] == group_val)]
    return sub.set_index(label_col)[value_col].sort_values(ascending=False)
