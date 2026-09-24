"""Aggregate Nigeria driver and barrier responses into the app table schema."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd

from pipeline.config import APP_DATA_DIR, WEIGHT_COL
from pipeline.utils import save


DRIVER_COLUMNS = ("Presentuser_drivers", "Intendeduser_drivers", "reason_use_mc")
BARRIER_COLUMNS = ("User_barriers", "Nonuser_barriers", "reason_nonuse_mc")
DRIVER_MAIN_COLUMNS = ("User_most_important_driver", "reason_use_main")
BARRIER_MAIN_COLUMNS = ("Nonuser_most_important_barrier", "reason_nonuse_main")
SPLITS = (
    ("use", "use"),
    ("age_group", "age_group"),
    ("gender", "gender"),
    ("region", "region"),
    ("urban_rural", "urban_rural"),
)


def _english_label(value):
    """Use bracketed English text when a choice label contains it."""
    text = str(value).strip()
    matches = re.findall(r"\(([^()]*)\)", text)
    return matches[-1].strip() if matches else text


def _choice_values(frame, columns):
    available = [column for column in columns if column in frame.columns]
    if not available:
        return pd.Series("", index=frame.index, dtype="string")
    values = frame[available].fillna("").astype("string").apply(
        lambda row: "|".join(value for value in row if value.strip()), axis=1
    )
    return values


def _contains_choice(values, choice):
    return values.fillna("").astype("string").str.split("|").apply(
        lambda parts: choice in {_english_label(part) for part in parts if part.strip()}
    )


def _format_metric(frame, mask, group_column=None):
    if group_column is None:
        groups = [("all", frame.index)]
    else:
        groups = frame.groupby(group_column, dropna=True).groups.items()

    prevalence = []
    raw_n = []
    weighted_n = []
    for group, indexes in groups:
        group_frame = frame.loc[indexes]
        valid = group_frame[WEIGHT_COL].notna()
        denominator = group_frame.loc[valid, WEIGHT_COL].sum()
        group_mask = mask.loc[indexes].fillna(False)
        weighted = group_frame.loc[group_mask & valid, WEIGHT_COL].sum()
        prevalence.append(f"{group}: {weighted / denominator * 100:.2f}%" if denominator else f"{group}: 0.0%")
        raw_n.append(f"{group}: {int(group_mask.sum())}")
        weighted_n.append(f"{group}: {group_frame.loc[group_mask & valid, WEIGHT_COL].sum():.1f}")
    return "\n".join(prevalence), "\n".join(raw_n), "\n".join(weighted_n)


def _weighted_choice_ranks(values, weights):
    rows = pd.DataFrame({"answer": values, "weight": weights}).dropna(subset=["answer"])
    rows["answer"] = rows["answer"].astype(str).str.split("|")
    rows = rows.explode("answer")
    rows["answer"] = rows["answer"].map(_english_label)
    totals = rows.groupby("answer")["weight"].sum().sort_values(ascending=False)
    return {name: rank for rank, name in enumerate(totals.index, start=1)}


def _priority_for(choice, values, main_values, weights):
    all_ranks = _weighted_choice_ranks(values, weights)
    main_ranks = _weighted_choice_ranks(main_values, weights)
    top = min(all_ranks.get(choice, 100), main_ranks.get(choice, 100))
    if top <= 3:
        return "Very high"
    if top <= 5:
        return "High"
    if top <= 7:
        return "Medium"
    return "Low"


def _focus_group(cell, threshold=1.3):
    if not cell:
        return ""
    values = {}
    for line in str(cell).split("\n"):
        match = re.match(r"^(.+?):\s*([\d.]+)%", line.strip())
        if match:
            values[match.group(1).strip()] = float(match.group(2))
    if not values:
        return ""
    average = sum(values.values()) / len(values)
    focused = [name for name, value in values.items() if value > average * threshold]
    return ", ".join(sorted(focused)) if focused else ", ".join(sorted(values))


def _statement_links():
    """Load optional analyst-reviewed Nigeria driver/barrier statement links."""
    path = Path(__file__).resolve().parents[2] / "nigeria_statement_links.csv"
    if not path.exists():
        return {}
    links = pd.read_csv(path).dropna(subset=["category", "label", "linked_statements"])
    return {
        (str(row.category), str(row.label)): [
            value.strip() for value in str(row.linked_statements).split(",") if value.strip()
        ]
        for row in links.itertuples()
    }


def _statement_cell(frame, statement_columns, category, choice, links, split_column=None):
    linked = links.get((category, choice), [])
    linked = [column for column in linked if column in frame.columns]
    if not linked:
        return ""
    values = frame[linked].apply(lambda column: column.astype("string").str.contains("agree|yes", case=False, na=False))
    if split_column is None:
        means = values.mean(axis=0).to_dict()
        return "\n".join(f"{column}: {mean * 100:.2f}%" for column, mean in means.items())
    rows = []
    for group, group_frame in frame.groupby(split_column, dropna=True):
        means = values.loc[group_frame.index].mean(axis=0)
        rows.append("\n".join(f"{group} — {column}: {mean * 100:.2f}%" for column, mean in means.items()))
    return "\n".join(rows)


def _statement_difference(frame, category, choice, links):
    columns = [column for column in links.get((category, choice), []) if column in frame.columns]
    if not columns or "use" not in frame.columns:
        return 0.0
    opinions = frame[columns].astype("string").apply(
        lambda column: column.str.contains("agree|yes", case=False, na=False)
    )
    current = opinions[frame["use"].eq("user")].mean(axis=0)
    nonuser = opinions[frame["use"].isin({"nonuser", "future_user", "past_user"})].mean(axis=0)
    differences = (current - nonuser).abs().dropna()
    return float(differences.mean() * 100) if not differences.empty else 0.0


def _priority_for_with_statements(choice, values, main_values, weights, frame, kind, links):
    top = min(
        _weighted_choice_ranks(values, weights).get(choice, 100),
        _weighted_choice_ranks(main_values, weights).get(choice, 100),
    )
    state_diff = _statement_difference(frame, kind, choice, links)
    if top <= 3 or state_diff >= 20 or (top <= 5 and state_diff >= 10):
        return "Very high"
    if top <= 5 or state_diff >= 15 or (top <= 7 and state_diff >= 10):
        return "High"
    if top <= 7 or state_diff >= 10 or (top <= 7 and state_diff >= 7):
        return "Medium"
    return "Low"


def _build_rows(frame, choices, values, main_values, kind, links):
    rows = []
    for choice in choices:
        mask = _contains_choice(values, choice)
        all_prevalence, all_n, all_weighted_n = _format_metric(frame, mask)
        main_mask = _contains_choice(main_values, choice)
        main_prevalence = _format_metric(frame, main_mask)[0]
        statement_columns = [column for column in frame.columns if column.startswith("statement_")]
        row = {
            "Name": choice,
            "Prevalence (All)": _format_metric(frame, mask, "use")[0],
            "N (All)": _format_metric(frame, mask, "use")[1],
            "Weighted N (All)": _format_metric(frame, mask, "use")[2],
            "Prevalence (Most important driver/barrier)": main_prevalence,
            "Statements": _statement_cell(frame, statement_columns, kind, choice, links),
            "Priority": _priority_for_with_statements(
                choice, values, main_values, frame[WEIGHT_COL], frame, kind, links
            ),
            "Driver/Barrier": kind,
        }
        for label, column in (
            ("AGE_GROUP", "age_group"),
            ("GENDER", "gender"),
            ("REGION", "region"),
            ("URBAN_RURAL", "urban_rural"),
        ):
            if column in frame.columns:
                prevalence, raw_n, weighted_n = _format_metric(frame, mask, column)
                main = _format_metric(frame, main_mask, column)[0]
            else:
                prevalence = raw_n = weighted_n = main = ""
            row[f"{label}: Prevalence (All)"] = prevalence
            row[f"{label}: N (All)"] = raw_n
            row[f"{label}: Weighted N (All)"] = weighted_n
            row[f"{label}: Prevalence (Most important driver/barrier)"] = main
            row[f"{label}: Statements"] = _statement_cell(frame, statement_columns, kind, choice, links, column)
            row[f"{label} Focus"] = _focus_group(prevalence)
        rows.append(row)
    return rows


def run(df):
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    print("  [drivers_barriers] running...")
    frame = df.copy()
    choices = {}
    for column_group in (DRIVER_COLUMNS, BARRIER_COLUMNS):
        values = _choice_values(frame, column_group)
        for value in values.str.split("|").explode().dropna().unique():
            if value.strip():
                choices.setdefault(_english_label(value), value)

    driver_values = _choice_values(frame, DRIVER_COLUMNS)
    barrier_values = _choice_values(frame, BARRIER_COLUMNS)
    driver_main = _choice_values(frame, DRIVER_MAIN_COLUMNS)
    barrier_main = _choice_values(frame, BARRIER_MAIN_COLUMNS)
    links = _statement_links()
    driver_choices = sorted({_english_label(value) for value in driver_values.str.split("|").explode().dropna() if value.strip()})
    barrier_choices = sorted({_english_label(value) for value in barrier_values.str.split("|").explode().dropna() if value.strip()})

    rows = _build_rows(frame, driver_choices, driver_values, driver_main, "driver", links)
    rows.extend(_build_rows(frame, barrier_choices, barrier_values, barrier_main, "barrier", links))
    result = pd.DataFrame(rows)
    save(result, os.path.join(APP_DATA_DIR, "drivers_barriers.csv"), "drivers and barriers")
    if links:
        print(f"  [drivers_barriers] applied {len(links)} analyst-reviewed statement links")
    else:
        print("  [drivers_barriers] no nigeria_statement_links.csv; Statements remain blank and priorities use rank only")
