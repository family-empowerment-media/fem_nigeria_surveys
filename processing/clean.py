"""Clean and normalize one Nigeria regional SurveyCTO export.

This module deliberately produces aggregate-safe diagnostics only. It preserves
survey columns in the cleaned output but never prints respondent records.
"""

from __future__ import annotations

import json
import re
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REGIONS = ("north", "south", "south_west")

ALIASES = {
    "gender": ("gender", "Selection_gender", "respondent_gender"),
    "age": ("age", "Selection_age", "respondent_age"),
    "occupation": ("occupation", "Occupation"),
    "religion": ("religion", "Religion"),
    "urban_rural": ("urban_rural", "Urban_semi-urban-rural", "Urban_semi_urban_rural"),
    "province": ("province", "State_North", "State_South_East", "State_South_West", "State"),
    "current_use": ("current_use", "Contraceptive_usage_female", "Contraception_usage_male"),
    "life_goals": ("life_goals", "Life_goals_most_wanted"),
    "reason_use_mc": ("reason_use_mc", "Presentuser_drivers", "Intendeduser_drivers"),
    "reason_nonuse_mc": ("reason_nonuse_mc", "User_barriers", "Nonuser_barriers"),
    "reason_use_main": ("reason_use_main", "User_most_important_driver"),
    "reason_nonuse_main": ("reason_nonuse_main", "Nonuser_most_important_barrier"),
    "reason_nonuse_main_other": ("reason_nonuse_main_other", "Nonuser_most_important_barrier_other"),
    "reason_nonuse_other": ("reason_nonuse_other", "Barrier_others"),
}

FORM_ALIASES = {
    "known_contraceptive_options": ("Contraceptive_method_awareness",),
    "ever_used_methods": ("User_method",),
    "current_use_methods": ("User_method",),
    "spacing_desire": ("Spacing_desire",),
    "reason_current_use": ("Presentuser_drivers",),
    "reason_current_nonuse": ("Nonuser_barriers",),
    "life_goals_main": ("Life_goals_most_wanted",),
    "role_models": ("Role_models",),
    "likeable_traits": ("Role_model_traits",),
    "forming_beliefs": ("Forming_health_believes",),
    "willingness_to_travel": ("Travel",),
    "travel_time_users": ("Travel_health_centre",),
    "travel_time_nonusers": ("Travel_health_centre",),
    "user_costs": ("User_contraceptive_cost",),
    "nonuser_cost": ("Nonuser_contraceptive_cost",),
}

SUPPORTED_ABSENT_FIELDS = (
    "time_before_preferred_pregnancy",
    "decision_confident",
    "decision_confident_3",
    "happiness",
    "satisfaction",
    "transport_mode_users",
    "transport_mode_nonusers",
)


def _first_present(frame: pd.DataFrame, names: tuple[str, ...]) -> str | None:
    return next((name for name in names if name in frame.columns), None)


def _form_choices(form_definition: str | Path | None) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    """Return choice maps and field -> choice-list maps from the XLSForm."""
    if form_definition is None:
        return {}, {}
    survey, choices = _read_xlsx_metadata(form_definition)
    choice_value_column = "name" if "name" in choices.columns else "value"
    choices = choices.dropna(subset=["list_name", choice_value_column, "label"])
    maps = {
        str(list_name): {
            str(value): str(label)
            for value, label in group[[choice_value_column, "label"]].itertuples(index=False)
        }
        for list_name, group in choices.groupby("list_name")
    }
    fields = {}
    for row in survey.itertuples(index=False):
        match = re.match(r"select_(?:one|multiple)\s+(.+)", str(row.type))
        if match:
            fields[str(row.name)] = match.group(1).strip()
    return maps, fields


def _read_xlsx_metadata(form_definition: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read the two XLSForm metadata sheets without requiring openpyxl."""
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    relationship_namespace = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    with ZipFile(form_definition) as archive:
        shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared = [
            "".join(text.text or "" for text in item.iter(namespace + "t"))
            for item in shared_root
        ]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}

        sheets = {}
        for sheet in workbook.find(namespace + "sheets"):
            relationship_id = sheet.attrib[relationship_namespace + "id"]
            target = targets[relationship_id].lstrip("/")
            sheets[sheet.attrib["name"]] = "xl/" + target.removeprefix("xl/")

        def read_sheet(name: str) -> pd.DataFrame:
            root = ET.fromstring(archive.read(sheets[name]))
            rows = []
            for row in root.findall(".//" + namespace + "row"):
                values = {}
                for cell in row.findall(namespace + "c"):
                    value = cell.find(namespace + "v")
                    text = "" if value is None else value.text or ""
                    if cell.attrib.get("t") == "s" and text:
                        text = shared[int(text)]
                    column = re.match(r"[A-Z]+", cell.attrib.get("r", ""))
                    if column:
                        values[column.group()] = text
                rows.append(values)
            if not rows:
                return pd.DataFrame()
            headers = rows[0]
            return pd.DataFrame([{header: row.get(column, "") for column, header in headers.items()} for row in rows[1:]])

        return read_sheet("survey"), read_sheet("choices")


def _decode_value(value, choice_map: dict[str, str], multiple: bool):
    if pd.isna(value) or not choice_map:
        return value
    text = str(value).strip()
    if not multiple:
        key = str(int(float(text))) if re.fullmatch(r"-?\d+(?:\.0+)?", text) else text
        return choice_map.get(key, value)
    decoded = []
    for token in re.split(r"[ ,]+", text):
        if not token:
            continue
        key = str(int(float(token))) if re.fullmatch(r"-?\d+(?:\.0+)?", token) else token
        decoded.append(choice_map.get(key, token))
    return "|".join(decoded) if decoded else value


def _decode_form_values(frame: pd.DataFrame, form_definition: str | Path | None) -> tuple[pd.DataFrame, dict[str, str]]:
    maps, fields = _form_choices(form_definition)
    result = frame.copy()
    decoded = {}
    for field, list_name in fields.items():
        if field not in result.columns or list_name not in maps:
            continue
        survey_types, _ = _read_xlsx_metadata(form_definition)
        field_types = survey_types.loc[survey_types["name"].eq(field), "type"]
        multiple = str(field_types.iloc[0] if not field_types.empty else "").startswith("select_multiple")
        result[field] = result[field].map(lambda value: _decode_value(value, maps[list_name], multiple))
        decoded[field] = list_name
    return result, decoded


def _canonicalize_columns(frame: pd.DataFrame, region: str, form_definition: str | Path | None) -> tuple[pd.DataFrame, dict[str, str], list[str]]:
    raw = frame.copy()
    result, decoded_fields = _decode_form_values(raw, form_definition)
    chosen: dict[str, str] = {}
    all_aliases = {**ALIASES, **FORM_ALIASES}
    for canonical, candidates in all_aliases.items():
        source = _first_present(result, candidates)
        if source and canonical not in result.columns:
            result[canonical] = result[source]
            chosen[canonical] = source

    result["survey_region"] = region
    if "region" not in result.columns:
        result["region"] = region.replace("_", " ").title()

    if "age" in result.columns and "age_group" not in result.columns:
        age = pd.to_numeric(result["age"], errors="coerce")
        result["age_group"] = pd.cut(
            age, bins=[15, 20, 30, 45], labels=["16-20", "21-30", "31-45"], right=True
        )

    usage_source = raw["Contraceptive_usage_female"] if "Contraceptive_usage_female" in raw else pd.Series(index=raw.index, dtype="float64")
    usage = pd.to_numeric(usage_source, errors="coerce")
    if usage.notna().any():
        result["use"] = usage.map({1: "nonuser", 2: "future_user", 3: "user", 4: "past_user"})
        result["current_use"] = usage.eq(3).map({True: "Oui", False: "Non"})
        result["ever_use"] = usage.isin([3, 4]).map({True: "Oui", False: "Non"})
        result["future_intent"] = usage.eq(2).map({True: "Oui", False: "Non"})

    if "known_contraceptive_options" in result.columns:
        result["birth_spacing"] = result["known_contraceptive_options"].notna().map({True: "Oui", False: "Non"})

    if "User_method_availability" in result:
        availability = result["User_method_availability"]
        availability_codes = pd.to_numeric(availability, errors="coerce")
        text = availability.astype("string").str.lower()
        result["stockouts_users"] = np.select(
            [availability_codes.isin([1, 2, 3, 4, 5]) | text.str.startswith("eh", na=False),
             availability_codes.isin([6, 7]) | text.str.startswith("a'a", na=False)],
            ["Non", "Oui"], default=pd.NA,
        )
    if "Nonuser_method_available" in result:
        availability = result["Nonuser_method_available"]
        availability = pd.to_numeric(availability, errors="coerce")
        result["stockouts_nonusers"] = np.select(
            [availability.eq(4), availability.isin([1, 2, 3])],
            ["Non", "Oui"], default=pd.NA,
        )

    for canonical in ("gender", "urban_rural"):
        if canonical in result.columns:
            text = result[canonical].astype("string")
            if canonical == "gender":
                result[canonical] = np.select(
                    [text.str.contains("female", case=False, na=False), text.str.contains("male", case=False, na=False)],
                    ["Female", "Male"], default=text,
                )
            else:
                result[canonical] = np.select(
                    [text.str.contains("Urban", case=False, na=False) & ~text.str.contains("semi", case=False, na=False),
                     text.str.contains("Semi", case=False, na=False), text.str.contains("Rural", case=False, na=False)],
                    ["Urban", "Semi-urban", "Rural"], default=text,
                )

    for binary_name in ("birth_spacing", "ever_use", "future_intent"):
        if binary_name in result.columns:
            values = result[binary_name].astype("string").str.strip().str.lower()
            yes = values.isin({"1", "yes", "y", "true", "oui"})
            no = values.isin({"0", "no", "n", "false", "non"})
            result[binary_name] = np.select([yes, no], ["Oui", "Non"], default=pd.NA)

    statement_sources = [c for c in result.columns if c.startswith("Agree_") or c.startswith("statement_")]
    for number, source in enumerate(statement_sources, start=1):
        target = source if source.startswith("statement_") else f"statement_{number}"
        if target not in result.columns:
            result[target] = result[source]

    statement_columns = [column for column in result.columns if column.startswith("statement_")]
    for column in statement_columns:
        text = result[column].astype("string").str.lower()
        result[column] = np.select(
            [text.str.contains("disagree|désaccord|rashin yarda", na=False),
             text.str.contains("agree|d'accord|yarda", na=False)],
            ["désaccord", "d'accord"], default=result[column],
        )

    if "life_goals_main" in result.columns:
        result["life_goals_main"] = result["life_goals_main"].astype("string").str.split("|").str[0]

    missing = [name for name in SUPPORTED_ABSENT_FIELDS if name not in result.columns]
    return result, {**chosen, "decoded_select_fields": ", ".join(sorted(decoded_fields))}, missing


def clean_region(
    raw_path: str | Path,
    output_path: str | Path,
    region: str,
    form_definition: str | Path | None = None,
    duration_minutes: float | None = None,
    missingness_threshold: float = 0.90,
) -> dict[str, Any]:
    if region not in REGIONS:
        raise ValueError(f"region must be one of {REGIONS}, got {region!r}")

    raw = pd.read_csv(raw_path, low_memory=False)
    raw.columns = raw.columns.astype(str).str.strip()
    input_rows, input_columns = len(raw), len(raw.columns)
    all_missing = raw.columns[raw.isna().all()].tolist()
    frame = raw.drop(columns=all_missing)

    if "duration" in frame.columns:
        duration = pd.to_numeric(frame["duration"], errors="coerce")
        if duration.notna().any() and duration.median() > 180:
            frame["duration"] = duration / 60

    unfinished = frame.isna().mean(axis=1) > missingness_threshold
    short = pd.Series(False, index=frame.index)
    if duration_minutes is not None and "duration" in frame.columns:
        short = pd.to_numeric(frame["duration"], errors="coerce") < duration_minutes
    excluded = unfinished | short
    frame = frame.loc[~excluded].copy()
    frame, chosen_aliases, absent_fields = _canonicalize_columns(frame, region, form_definition)
    frame = frame.copy()

    weight_source_column = next(
        (name for name in (
            "combined_weight_adjusted", "normalized_weight",
            "combined_weight", "weight",
        ) if name in frame.columns),
        None,
    )
    if weight_source_column is None:
        frame["normalized_weight"] = 1.0
        weight_source = "unit weight (no survey weight supplied)"
    else:
        frame["normalized_weight"] = pd.to_numeric(
            frame[weight_source_column], errors="coerce"
        )
        weight_source = weight_source_column
    frame["combined_weight_adjusted"] = frame["normalized_weight"]

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)

    manifest = {
        "region": region,
        "input_path": str(raw_path),
        "output_path": str(output),
        "input_rows": input_rows,
        "output_rows": len(frame),
        "input_columns": input_columns,
        "output_columns": len(frame.columns),
        "dropped_all_missing_columns": all_missing,
        "excluded_unfinished_rows": int(unfinished.sum()),
        "excluded_short_duration_rows": int(short.sum()),
        "missingness_threshold": missingness_threshold,
        "duration_minutes": duration_minutes,
        "weight_source": weight_source,
        "canonical_aliases": chosen_aliases,
        "unsupported_or_absent_fields": absent_fields,
        "missing_canonical_fields": [
            name for name in (
                "gender", "age", "province", "use", "combined_weight_adjusted",
            )
            if name not in frame.columns
        ],
    }
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
