"""
Shared ETL helper functions used across all pipeline modules.
No PII is returned from these functions — only aggregated statistics.
"""

import pandas as pd
import numpy as np
from pipeline.config import WEIGHT_COL


# ── Weighted aggregation ──────────────────────────────────────────────────────

def weighted_prop(df, bool_col, weight=WEIGHT_COL):
    """Weighted proportion for a boolean/binary column."""
    valid = df[[bool_col, weight]].dropna()
    if valid.empty or valid[weight].sum() == 0:
        return np.nan
    return (valid[bool_col] * valid[weight]).sum() / valid[weight].sum()


def weighted_mean(df, num_col, weight=WEIGHT_COL):
    valid = df[[num_col, weight]].dropna()
    if valid.empty or valid[weight].sum() == 0:
        return np.nan
    return (valid[num_col] * valid[weight]).sum() / valid[weight].sum()


def weighted_counts(df, col, label_map=None, weight=WEIGHT_COL,
                    exclude=(-88, -99, -22)):
    """
    Weighted proportion for each category of a single-select column.
    Returns a Series: label -> proportion (0-1).
    """
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


def weighted_multiselect_counts(df, col, label_map=None, weight=WEIGHT_COL,
                                sep=" "):
    """
    Weighted counts for a select_multiple column (space-separated integers).
    Proportions are relative to total respondents (not total responses).
    """
    rows = []
    for _, row in df[[col, weight]].dropna().iterrows():
        for v in str(row[col]).split(sep):
            try:
                vi = int(v)
                if vi not in (-88, -99):
                    rows.append({"value": vi, weight: row[weight]})
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


# ── Split helpers ─────────────────────────────────────────────────────────────

def split_weighted_prop(df, bool_col, split_col, weight=WEIGHT_COL):
    """Weighted proportion of bool_col for each group in split_col."""
    result = {}
    for grp, gdf in df.groupby(split_col):
        result[grp] = weighted_prop(gdf, bool_col, weight)
    return pd.Series(result).dropna()


def split_weighted_mean(df, num_col, split_col, weight=WEIGHT_COL):
    result = {}
    for grp, gdf in df.groupby(split_col):
        result[grp] = weighted_mean(gdf, num_col, weight)
    return pd.Series(result).dropna()


def split_weighted_counts(df, col, split_col, label_map=None,
                          weight=WEIGHT_COL, exclude=(-88, -99, -22)):
    """
    Returns a DataFrame: rows=labels, columns=split groups, values=proportions.
    """
    frames = {}
    for grp, gdf in df.groupby(split_col):
        frames[grp] = weighted_counts(gdf, col, label_map, weight, exclude)
    return pd.DataFrame(frames).fillna(0)


def split_weighted_multiselect(df, col, split_col, label_map=None,
                               weight=WEIGHT_COL, sep=" "):
    """
    Returns a DataFrame: rows=labels, columns=split groups, values=proportions.
    """
    frames = {}
    for grp, gdf in df.groupby(split_col):
        frames[grp] = weighted_multiselect_counts(gdf, col, label_map, weight, sep)
    return pd.DataFrame(frames).fillna(0)


# ── IO ────────────────────────────────────────────────────────────────────────

def save(df, path, description=""):
    """Save a DataFrame to CSV, printing a summary."""
    df.to_csv(path)
    print(f"  Saved {description}: {path}  ({len(df)} rows x {df.shape[1]} cols)")


def load_raw(path):
    """Load the PII dataset."""
    df = pd.read_csv(path, low_memory=False)
    df.columns = df.columns.str.strip()
    print(f"  Loaded raw data: {len(df)} rows, {df.shape[1]} columns")
    return df
