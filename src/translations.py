"""
src/translations.py — "Show in English" toggle support.

Benin's survey is in French/Fon; the app displays French by default. This module
provides AI-generated (Claude) English translations for the free-text vocabulary
that appears in the app's charts and tables -- driver/barrier names, belief
statements, occupation/religion categories, etc.

IMPORTANT: these are machine-translated by Claude from the French source text, not
an official or certified translation. Wherever the toggle is on, the app must show
the disclaimer in DISCLAIMER_TEXT so readers know not to treat the English wording
as authoritative -- see render_toggle().

Usage in a page module:
    from src.translations import tr, is_english()
    label = tr(_strip_hausa(raw_name))   # translates only if the toggle is on
"""

from pathlib import Path

import streamlit as st
import pandas as pd

# Resolve relative to this file, not the process cwd -- these two translation
# tables are shipped in the repo (small, static, versioned alongside the code),
# unlike the rest of benin_app's data which is Drive-hosted.
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DISCLAIMER_TEXT = (
    "🌐 English text is AI-translated (Claude) from the original French/Fon survey "
    "data for readability -- it is not an official or certified translation. "
    "Refer to the French for anything that will be quoted or published."
)

SESSION_KEY = "show_english"

# ── Small controlled vocabularies (hand-authored, AI-translated) ────────────────

OCCUPATION_EN = {
    "Aide ménagère": "Domestic helper",
    "Artisan": "Artisan",
    "Autre": "Other",
    "Dans les transports": "In transportation",
    "Femme au foyer": "Housewife",
    "Fermier, agriculteur, pêcheur": "Farmer, agriculturalist, fisherman",
    "Médecine traditionnelle": "Traditional medicine",
    "Ouvrier du bâtiment": "Construction worker",
    "Personnel religieux": "Religious personnel",
    "Petits boulots": "Odd jobs",
    "Professionnel de santé paramédical": "Paramedical health professional",
    "Retraité(e)": "Retired",
    "Secteur privé": "Private sector",
    "Secteur public": "Public sector",
    "Vendeur ou petit commerçant": "Vendor or small trader",
    "Étudiant(e)": "Student",
}

RELIGION_EN = {
    "Aucune": "None",
    "Autre": "Other",
    "Christianisme": "Christianity",
    "Islam": "Islam",
    "Préfère ne pas répondre": "Prefer not to say",
    "Traditionnelle": "Traditional",
}

URBAN_RURAL_EN = {
    "Rural": "Rural",
    "Semi-urbain": "Semi-urban",
    "Urbain": "Urban",
}

GENDER_RAW_EN = {
    "Femme Nyɔnu": "Woman",
    "Homme Sunnu": "Man",
    "Femme": "Woman",
    "Homme": "Man",
}


@st.cache_data(show_spinner=False)
def _load_statement_dict():
    try:
        df = pd.read_csv(_DATA_DIR / "statement_labels.csv")
        return dict(zip(df["label_fr"], df["label_en"]))
    except Exception:
        return {}


@st.cache_data(show_spinner=False)
def _load_driver_barrier_dict():
    try:
        df = pd.read_csv(_DATA_DIR / "driver_barrier_translations.csv")
        return dict(zip(df["label_fr"], df["label_en"]))
    except Exception:
        return {}


@st.cache_data(show_spinner=False)
def _load_radio_dict():
    # 2026-08-27: radio page's choice-list answers (media type, radio_when,
    # etc.) -- keyed on the French-only label left after etl_radio.py's
    # strip_fon() runs, same convention as the other tables here.
    try:
        df = pd.read_csv(_DATA_DIR / "radio_translations.csv")
        return dict(zip(df["label_fr"], df["label_en"]))
    except Exception:
        return {}


def _combined_dict():
    d = {}
    d.update(OCCUPATION_EN)
    d.update(RELIGION_EN)
    d.update(URBAN_RURAL_EN)
    d.update(GENDER_RAW_EN)
    d.update(_load_statement_dict())
    d.update(_load_driver_barrier_dict())
    d.update(_load_radio_dict())
    return d


def is_english() -> bool:
    return bool(st.session_state.get(SESSION_KEY, False))


def tr(text, sep="|"):
    """
    Translate `text` to English if the toggle is on, else return it unchanged.
    Handles `sep`-joined multi-select values (e.g. occupation) by translating
    each piece and rejoining with "; ". Falls back to the original text for
    anything not in the lookup (so nothing silently disappears).
    """
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return text
    if not is_english():
        return text

    d = _combined_dict()
    text = str(text)
    if sep in text:
        parts = [p.strip() for p in text.split(sep)]
        return "; ".join(d.get(p, p) for p in parts if p)
    return d.get(text, text)


def render_toggle():
    """Sidebar/top-of-page toggle + disclaimer. Call once near the top of app.py."""
    st.session_state.setdefault(SESSION_KEY, False)
    st.checkbox(
        "🌐 Show in English (AI-translated)",
        key=SESSION_KEY,
        help=DISCLAIMER_TEXT,
    )
    if is_english():
        st.caption(DISCLAIMER_TEXT)
