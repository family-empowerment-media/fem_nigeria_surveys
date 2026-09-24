import os
import re
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Nigeria aggregate loaders (safe: no PII) ──────────────────────────────

REGIONS = ("north", "south", "south_west")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = Path(os.environ.get("FEM_APP_DATA_ROOT", PROJECT_ROOT / "data"))

NORTH_DRIVE_IDS = {
    "drivers_barriers.csv": "1Oya_jnBzgz-HvmwA9kbz7xma1U_A8k8v",
    "access_affordability.csv": "1i1dtZBQBCBFvodIeC7lwYCeb-P5QNVd3",
    "access_composite.csv": "1hbk5vA2gQCFeNqNqXZm1rFzChuTBJ5ay",
    "access_stockouts.csv": "1JD0pd7Aoqa1vr61dw9zEV4bZC0Bah8-c",
    "access_travel.csv": "1Ax0n_8ixAIpjOO_0fm_739WoAIWWvsUf",
    "culture_clusters_centroids.csv": "1pfoSFiPaMYJ5xHcMM15YLTiaF-a7n19V",
    "culture_clusters_elbow.csv": "1dHKSwSuWkGVInFuzD5lqLGG12pAmfVOv",
    "culture_clusters_profile.csv": "1kD2SQghb2FWLOH7seiVnpAmI5sHwLaeM",
    "fp_funnel.csv": "1Nd26h26CmagA888FscmigWAQgPkyotdG",
    "fp_intent.csv": "1Nd26h26CmagA888FscmigWAQgPkyotdG",
    "fp_methods.csv": "11GYwaB7INsr7wWfO5hKAYADJraf75UH0",
    "fp_nonuse_reasons.csv": "1641rS3UetvwZUVf0ieS1k0i9reh8x02w",
    "fp_reason_use.csv": "166UFYjAeYK9RmAxAVvM6fjIvUYRUBi_j",
    "fp_unmet.csv": "1LZWDOvMBv4f2dzKBsIbqr_f8Di32JkTx",
    "personality_forming_beliefs.csv": "1EXuFYENIJhmC7AxDZDqAtSNa-O3cosZY",
    "personality_life_goals.csv": "1tx-k6GB2HckdqGX4iwAuV_opVx_r3ZTr",
    "personality_likeable_traits.csv": "1dgfKNJ1B_pF0ffVUS75ItpMhxaeP3kWU",
    "personality_role_models.csv": "1y9WSBbBy7QaTFiiOFNizN3IJfKrKY8O5",
    "personas_centroids.csv": "1FiIV8mYuXMwJRi50BA7Hu3bNK0rVQHId",
    "personas_profile.csv": "1Si8ihAbnrf8zUjg9z-_4pK82qkcBkWYs",
    "respondents_profile.csv": "1IUHEmaabqJOqJh9qmkhhytNVPgM1vHVw",
    "statements_heatmap.csv": "1g1761-pevXHHa_QFmet62dSm1GTJJTUi",
}

SOUTH_DRIVE_IDS = {
    "drivers_barriers.csv": "1kbAqsiHxE0SND7XXVRBw9yWTT8r2Rq79",
    "access_affordability.csv": "1hg21MpdWX6wloPnGmelMHTBRRWRnZryI",
    "access_composite.csv": "14kSwgAbL_tdolMpZdnKZhBBtSB716vqo",
    "access_stockouts.csv": "1wR7zFGgNgr47zV0meHeavR2Klsdwrh27",
    "access_travel.csv": "1u1PvI8u1PGNgcspFZmtaZudBs-vR4k4a",
    "culture_clusters_centroids.csv": "1KUSaAqq5z_JZfvomiUKu6e0DpoGYfz6e",
    "culture_clusters_elbow.csv": "11U5v1RquRwesl1ohmFtLFJH1JpAoA7E5",
    "culture_clusters_profile.csv": "1HGLxn0_H3VGs9wPstGj9KwWECy8gTbTm",
    "fp_funnel.csv": "1Bh9hzrBSBQyjMH3yRXxgU0NxaprUj5-W",
    "fp_intent.csv": "1PAZLPZvlic2hCLmFMsWVOh6jprRcrhxr",
    "fp_methods.csv": "19ntLVSx18HRBN2sLduFQXPoNhnq4kF19",
    "fp_nonuse_reasons.csv": "1UYrS2Bd0VM6EXttDGZ_U5z3VfAPCkCJY",
    "fp_reason_use.csv": "1G1Uf4Q6PUCowl2urnbNMHBkX9_dnq8Ra",
    "fp_unmet.csv": "1oYJlDcPJHDAmL__9JH_ItxGuiScxQC4G",
    "personality_forming_beliefs.csv": "1WoOrzqmHR9QH3lSHFMj-WoJYh7zqRgDW",
    "personality_life_goals.csv": "1fyf90LQUtS6_nBaok9fP6TNb9JqTpDW4",
    "personality_likeable_traits.csv": "1fdF1_6qVwi_eEQoj-i0VVHr4L1H-IFgy",
    "personality_role_models.csv": "14ScgYusK2y-6dzyu_8sAnrGeme7VYalI",
    "personas_centroids.csv": "17ktRaL0probkKbcttfU2ALN-0GHG2Iha",
    "personas_profile.csv": "1mRoADpH8R01iWvuWGfwCP9xC5qsjNI9V",
    "respondents_profile.csv": "1YcNPPgd_Nkv5FxLaMUrGBwOHLlZ_gYsm",
    "statements_heatmap.csv": "1P5NjvhJDzuqwZvv93l1yEn4xg4A7gcQE",
}


SOUTH_WEST_DRIVE_IDS = {
    "drivers_barriers.csv": "1X8oKvYzWS4vrulsBtXpxJ0WT0i-lKZOJ",
    "access_affordability.csv": "1CFBriweeLxGD9pAg0gi_TQJxoiZYsiiq",
    "access_composite.csv": "1yJfpqZ2YJf_HO7PPILAEEYZtrWDyrHnT",
    "access_stockouts.csv": "1e5lq0CC1S_8Yun3chocHw0oQ0eiweMU8",
    "access_travel.csv": "1SerdaXriadt_i9TCELAz_WHVjnMeVy_Z",
    "culture_clusters_centroids.csv": "1RktV_q2cN4mdvAhsS9mr6x9knzTetE3l",
    "culture_clusters_elbow.csv": "1ktFFKcAM62cNtE_73eX1qIfx5TGtESzN",
    "culture_clusters_profile.csv": "1SbeKuu6irc_2GG9GBULIRpA8RyoKTTim",
    "fp_funnel.csv": "1-XRO6sT3-eDlzWPWqR5xGl02r-i05w7c",
    "fp_intent.csv": "1S1Ltx56CuiMuVfDxuUnA5nAb92U-lJmL",
    "fp_methods.csv": "1YTFaHDngBbDnFmGc8HYUPa4UY4Jw8vxD",
    "fp_nonuse_reasons.csv": "1W8486XzWcjnZci-83FzX0bJCBz1i_3na",
    "fp_reason_use.csv": "1IWpU-IAF2zkoI57kn3HQnmzJPbbEh0B2",
    "fp_unmet.csv": "1A71JqdEOwD_bVOZ96tmxMP35NHsmGPSu",
    "personality_forming_beliefs.csv": "1tS1g5PQ1o5c3uHhjyF_UDtJpDEPejyqV",
    "personality_life_goals.csv": "1u5zcZSABQ6h-kJvyjudDqnVikYDLKtwj",
    "personality_likeable_traits.csv": "1R9C2pEMFlBt5XPq2GvRHj0-6B13tSPCg",
    "personality_role_models.csv": "1SacC8X2_Aq48PH_BJxCO9fMt5ZqMAwJX/",
    "personas_centroids.csv": "1_YIJOebK3Ci4XWfm1qrjs8wZS57r6cdX",
    "personas_profile.csv": "1KqOK8suOYzald7iKbAc6TxxUMVZKB-wF/",
    "respondents_profile.csv": "1VSMRf0YVaXox-dTufrswGmGUFHRxhgjC",
    "statements_heatmap.csv": "1HbbuOKa0scsov0jnPVTZDtyEtRTke2PA",
}

def _selected_region():
    region = st.session_state.get("survey_region", "north")
    if region not in REGIONS:
        raise ValueError(f"survey_region must be one of {REGIONS}, got {region!r}")
    return region


def _load(filename, **kwargs):
    """Load a local aggregate, falling back to its configured Drive copy."""
    region = _selected_region()
    path = DATA_ROOT / region / filename
    if path.exists():
        return pd.read_csv(path, **kwargs)

    drive_ids = {
        "north": NORTH_DRIVE_IDS,
        "south": SOUTH_DRIVE_IDS,
        "southwest": SOUTH_WEST_DRIVE_IDS,
    }.get(region, {})
    file_id = drive_ids.get(filename)
    if file_id is None:
        return None
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    return pd.read_csv(url, **kwargs)


# ── Statements / drivers-barriers ──────────────────────────────────────────

def load_statement_labels():
    return _load("statement_labels.csv")


def load_statements_heatmap():
    return _load("statements_heatmap.csv", index_col=0)


# ── Access page ──────────────────────────────────────────────────────────────

def load_access_stockouts():
    return _load("access_stockouts.csv", index_col=0)


def load_access_stockout_responses():
    return _load("access_stockout_responses.csv", index_col=0)


def load_access_travel():
    return _load("access_travel.csv", index_col=0)


def load_access_affordability():
    return _load("access_affordability.csv", index_col=0)


def load_access_composite():
    return _load("access_composite.csv", index_col=0)


# ── Radio page ───────────────────────────────────────────────────────────────

def clean_column_name(col):
    col = re.sub(r'^\d+_\d+_', '', col)
    col = re.sub(r'_+\d+$', '', col)
    col = col.replace('_', ' ').strip().title()
    return col


def load_radio_by_station():
    df = _load("Nigeria_question_table_by_station.csv")
    if df is None:
        return None
    df.set_index(df.columns[0], inplace=True)
    return df


def load_radio_by_state():
    df = _load("Nigeria_question_table_by_state.csv")
    if df is None:
        return None
    df.set_index(df.columns[0], inplace=True)
    return df


# ── Family planning page ──────────────────────────────────────────────────────

def load_fp_funnel():
    return _load("fp_funnel.csv", index_col=0)


def load_fp_timing():
    return _load("fp_timing.csv", index_col=0)


def load_fp_methods():
    return _load("fp_methods.csv", index_col=0)


def load_fp_reason_use():
    return _load("fp_reason_use.csv", index_col=0)


def load_fp_intent():
    return _load("fp_intent.csv", index_col=0)


def load_fp_nonuse_reasons():
    return _load("fp_nonuse_reasons.csv", index_col=0)


def load_fp_unmet():
    return _load("fp_unmet.csv", index_col=0)


# ── Personality page ──────────────────────────────────────────────────────────

def load_personality_life_goals():
    return _load("personality_life_goals.csv", index_col=0)


def load_personality_goals_achievable():
    return _load("personality_goals_achievable.csv", index_col=0)


def load_personality_role_models():
    return _load("personality_role_models.csv", index_col=0)


def load_personality_likeable_traits():
    return _load("personality_likeable_traits.csv", index_col=0)


def load_personality_forming_beliefs():
    return _load("personality_forming_beliefs.csv", index_col=0)


def load_personality_decision_confident():
    return _load("personality_decision_confident.csv", index_col=0)


def load_personality_wellbeing():
    return _load("personality_wellbeing.csv", index_col=0)


# ── Respondent profile page ───────────────────────────────────────────────────

def load_respondents_profile():
    return _load("respondents_profile.csv", index_col=0)


# ── Personas page ─────────────────────────────────────────────────────────────

def load_personas_centroids():
    return _load("personas_centroids.csv", index_col=0)


def load_personas_profile():
    return _load("personas_profile.csv", index_col=0)


def load_personas_centroids_by_gender():
    return _load("personas_centroids_by_gender.csv", index_col=0)


def load_personas_profile_by_gender():
    return _load("personas_profile_by_gender.csv", index_col=0)


def load_personas_elbow():
    return _load("personas_elbow.csv", index_col=0)


# Region-split personas (added 2026-08-24, mirrors the by-gender split above).
def load_personas_centroids_by_region():
    return _load("personas_centroids_by_region.csv", index_col=0)


def load_personas_profile_by_region():
    return _load("personas_profile_by_region.csv", index_col=0)


def load_personas_elbow_by_region():
    return _load("personas_elbow_by_region.csv", index_col=0)


# Standalone culture clustering (religion, life goals, top driver/barrier --
# region deliberately excluded as a clustering input, see
# CULTURE_CLUSTERING_VARS in pipeline/config.py) -- added 2026-09-02 to test
# whether cultural traits geographically concentrate. Same upload status as
# the North/South split above.
def load_culture_clusters_centroids():
    return _load("culture_clusters_centroids.csv", index_col=0)


def load_culture_clusters_profile():
    return _load("culture_clusters_profile.csv", index_col=0)


def load_culture_clusters_elbow():
    return _load("culture_clusters_elbow.csv", index_col=0)


# ── Drivers & barriers ──────────────────────────────────────────────────────
def load_drivers_barriers():
    return _load("drivers_barriers.csv")


# ── Phone Pulse pages ───────────────────────────────────────────────────────
# Nigeria phone-pulse outputs are not part of this baseline pipeline.


# ── Shared parsing helpers (used by drivers/barriers) ──────────────────────

def parse_subgroup_prevalence(cell_str):
    result = {}
    if pd.isna(cell_str) or str(cell_str).strip() == "":
        return result
    for line in str(cell_str).split("\n"):
        line = line.strip()
        match = re.match(r"^(.+?):\s*([\d.]+)%", line)
        if match:
            result[match.group(1).strip()] = float(match.group(2))
    return result


def parse_statements(cell_str):
    if pd.isna(cell_str) or str(cell_str).strip() == "":
        return None, {}
    lines = [l.strip() for l in str(cell_str).split("\n") if l.strip()]
    statement = None
    percentages = {}
    for line in lines:
        match = re.match(r"^(.+?):\s*([\d.]+)%", line)
        if match:
            percentages[match.group(1).strip()] = float(match.group(2))
        elif statement is None and "%" not in line:
            statement = line
    return statement, percentages


PRIORITY_ORDER = {"Very high": 4, "High": 3, "Medium": 2, "Low": 1}


def get_priority_sort_key(p):
    return PRIORITY_ORDER.get(str(p).strip(), 0)


USER_CATEGORY_LABELS = {
    "user":        "Current user",
    "nonuser":     "Non-user",
    "future_user": "Future user",
    "past_user":   "Past user",
}

AGE_GROUPS  = ["16-20", "21-30", "31-45"]
# NOTE: the drivers/barriers table (table_analysis/03_driver_barrier_table_w_counts.ipynb)
# splits on the raw, unprocessed 'gender' column ("Femme Nyɔnu"/"Homme Sunnu"),
# not the cleaned "Femme"/"Homme" used in respondents_profile.csv etc. -- verified
# against the actual GENDER: columns in Benin_drivers-barriers_table_*.csv.
GENDERS     = ["Femme Nyɔnu", "Homme Sunnu"]
URBAN_RURAL = ["Rural", "Semi-urbain", "Urbain"]  # verified against the actual weighted data's urban_rural values

