import streamlit as st
import pandas as pd
import re
import plotly.graph_objects as go
import plotly.express as px
from src.fem_colours import FEM_ORANGE, FEM_BROWN, FEM_TAUPE, FEM_STEEL, FEM_NAVY, FEM_PALETTE
from src.data_loader import (
    load_personas_centroids,
    load_personas_profile,
    load_personas_centroids_by_gender,
    load_personas_profile_by_gender,
    load_personas_elbow,
    load_personas_centroids_by_region,
    load_personas_profile_by_region,
    load_personas_elbow_by_region,
    load_culture_clusters_centroids,
    load_culture_clusters_profile,
    load_culture_clusters_elbow,
    REGIONS,
)
from src.translations import tr

_MISSING = (
    "Pre-aggregated persona data not found. "
    "Run `python -m pipeline.run_pipeline --pages personas` (from pipeline_output/) to generate it."
)

PROFILE_VARS = ["gender", "age_group", "use", "occupation", "religion", "life_goals"]

# Raw 'gender' values are unprocessed bilingual text (etl_personas.py clusters
# on the raw survey column directly, doesn't run it through _clean_bilingual).
GENDER_DISPLAY = {
    "Femme Nyɔnu": "Femme",
    "Homme Sunnu": "Homme",
}
GENDER_COLORS = {
    "Femme Nyɔnu": FEM_ORANGE,
    "Homme Sunnu": FEM_NAVY,
}


# ── Chart helpers ─────────────────────────────────────────────────────────────

# 2026-09-04: Fon uses IPA Extensions letters (ɖ, ɔ, ɛ, ɥ, ...) that never
# appear in French, so the true French/Fon boundary is the LAST '/' before
# the first such character -- not simply the first '/' in the string. Some
# choice labels' French half contains its own slash (e.g. life_goals value 6,
# "Une bonne/meilleure santé personnelle/ Lanmɛ ɖagbe/..."), and splitting on
# the first '/' truncated those to "Une bonne", silently dropping the rest of
# that item and anything pipe-joined after it -- this is what a persona's
# top_driver showing "...|Une bonne" as if it were a complete value turned
# out to be. Same fix needed in etl_personas.py's _strip_fon (the copy that
# builds top_driver/top_barrier before this ever renders); the copies in
# etl_family_planning.py and page_drivers_barriers.py carry the same naive
# split and may have the same latent bug on other choice lists.
_FON_CHAR_RE = re.compile(r"[ɐ-ʯ]")


def _split_french_fon(item: str) -> str:
    """French half of ONE bilingual 'French/Fon' label (already pipe-split)."""
    m = _FON_CHAR_RE.search(item)
    if not m:
        # No Fon-specific character found -- fall back to the old behavior
        # rather than guess.
        if "/" in item:
            french = item.split("/", 1)[0].strip()
            return french if french else item.strip()
        return item.strip()
    boundary = item.rfind("/", 0, m.start())
    if boundary == -1:
        return item.strip()
    french = item[:boundary].strip()
    return french if french else item.strip()


def _strip_hausa(text: str) -> str:
    """Return only the French part of bilingual 'French/Fon' labels (Benin's
    order -- first segment, not last)."""
    if not text or pd.isna(text):
        return str(text).strip()
    text = str(text)
    if "|" in text:
        parts = text.split("|")
        return "|".join(_strip_hausa(p) for p in parts)
    return _split_french_fon(text)


_VAR_LABEL_OVERRIDES = {
    "age_gender_combo": "Age × Gender",
    "top_driver": "Top driver (use)",
    "top_barrier": "Top barrier (non-use)",
}


def _var_label(var):
    return _VAR_LABEL_OVERRIDES.get(var, var.replace("_", " ").title())


def _hbar(series, title, top_n=10, key=None):
    series = series.head(top_n)
    if series is None or series.empty:
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
        height=max(180, len(series) * 34 + 60),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


# ── Elbow plot ────────────────────────────────────────────────────────────────

def render_elbow_plot(df_elbow, split_col="gender", key="elbow_plot"):
    st.subheader("Choosing the number of clusters")
    label_map = GENDER_DISPLAY if split_col == "gender" else {}
    color_map = GENDER_COLORS if split_col == "gender" else {}
    split_noun = "female and male respondents" if split_col == "gender" else "each region"
    has_chosen_k = "chosen_k" in df_elbow.columns
    st.caption(
        "Each line shows the within-cluster cost (sum of dissimilarities) for "
        f"k = 1 – 6 clusters, computed separately for {split_noun}. "
        "The 'elbow' — where the curve flattens — indicates the optimal k."
        + (" The marked point is the k this group was actually clustered with "
           "(auto-selected from this curve, not fixed)." if has_chosen_k else "")
    )

    groups = df_elbow[split_col].unique()
    fig = go.Figure()
    for i, g in enumerate(groups):
        sub = df_elbow[df_elbow[split_col] == g].sort_values("k")
        color = color_map.get(g, FEM_PALETTE[i % len(FEM_PALETTE)])
        label = tr(label_map.get(g, g))
        chosen_k = int(sub["chosen_k"].iloc[0]) if has_chosen_k and not sub.empty else None
        fig.add_trace(go.Scatter(
            x=sub["k"], y=sub["cost"],
            mode="lines+markers",
            name=f"{label} (k={chosen_k})" if chosen_k else label,
            line=dict(color=color, width=2),
            marker=dict(
                size=[14 if k == chosen_k else 7 for k in sub["k"]],
                symbol=["star" if k == chosen_k else "circle" for k in sub["k"]],
            ),
        ))

    fig.update_layout(
        xaxis=dict(title="Number of clusters (k)", dtick=1, showgrid=False),
        yaxis=dict(title="Within-cluster cost", showgrid=True, gridcolor="#eeeeee"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(title=split_col.title(), bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=10, t=10, b=10),
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


# ── Section renderers ─────────────────────────────────────────────────────────

def _top_real_value(df_profile, persona_id, col):
    """Best non-'Unknown' value for one persona/column from its profile
    breakdown (top-3 by share), or None if it's genuinely all-Unknown.

    Needed because top_driver/top_barrier only apply to half the sample each
    (top_driver=users only, top_barrier=non-users only) -- k-modes' centroid
    for that column is a legitimate joint-optimization mode across all 7
    clustering variables, but for a column this fragmented (dozens of
    specific reasons, each a small slice) 'Unknown' can win that slot even
    when the persona's own profile shows more informative real signal in its
    top values. The centroid table should surface that instead.
    """
    if df_profile is None or df_profile.empty:
        return None
    sub = df_profile[
        (df_profile["persona"] == persona_id) &
        (df_profile["variable"] == col) &
        (df_profile["value"] != "Unknown")
    ]
    if sub.empty:
        return None
    return sub.sort_values("proportion", ascending=False)["value"].iloc[0]


def render_centroid_table(df_centroids, df_profile=None, split_label=None, split_col="gender"):
    st.subheader("Persona summary")
    st.caption(
        "Each row is a cluster centroid — the representative values for that persona. "
        "Count shows the number of respondents in each cluster."
    )

    display = df_centroids.copy()
    # top_driver/top_barrier: prefer the persona's top real (non-"Unknown")
    # value from its profile breakdown over the raw centroid -- see
    # _top_real_value's docstring for why the centroid alone can be
    # "Unknown" even when real signal exists.
    for col in ("top_driver", "top_barrier"):
        if col in display.columns and "persona" in display.columns:
            display[col] = display.apply(
                lambda row: _top_real_value(df_profile, row["persona"], col) or row[col],
                axis=1,
            )

    # Drop "persona" (just the row index) and the split column itself (constant
    # within this table, already shown by the tab it's under) -- but keep any
    # *other* clustering variable, e.g. "gender" is a real feature when split_col
    # is "region", not just bookkeeping.
    display.drop(columns=["persona", split_col], inplace=True, errors="ignore")
    for col in ("occupation", "religion", "life_goals", "top_driver", "top_barrier"):
        if col in display.columns:
            display[col] = display[col].apply(lambda x: tr(_strip_hausa(x)))
    if "gender" in display.columns:
        display["gender"] = display["gender"].map(GENDER_DISPLAY).fillna(display["gender"])

    for col in ["age", "count", "weighted_count"]:
        if col in display.columns and display[col].dtype in [int, float]:
            display[col] = display[col].apply(
                lambda v: f"{int(v):,}" if pd.notna(v) else ""
            )

    display.columns = [col.replace("_", " ").title() for col in display.columns]
    st.dataframe(display, use_container_width=True)


def render_persona_profiles(df_profile, n_personas, split_label=None):
    key_suffix = split_label.replace(" ", "_").replace("/", "") if split_label else "overall"
    st.subheader("Persona deep-dive")
    st.caption("Select a persona to see the distribution of key variables within that cluster.")

    persona_id = st.selectbox(
        "Select persona",
        list(range(n_personas)),
        format_func=lambda x: f"Persona {x}",
        key=f"persona_select_{key_suffix}",
    )

    sub = df_profile[df_profile["persona"] == persona_id].copy()

    count_row = sub[sub["variable"] == "_count"]
    if not count_row.empty:
        n = count_row[count_row["value"] == "n"]["proportion"].values
        wn = count_row[count_row["value"] == "weighted_n"]["proportion"].values
        c1, c2 = st.columns(2)
        c1.metric("Respondents", f"{int(n[0]):,}" if len(n) else "N/A")
        c2.metric("Weighted N", f"{wn[0]:,.0f}" if len(wn) else "N/A")

    profile_vars = [v for v in sub["variable"].unique() if not v.startswith("_")]
    cols = st.columns(2)
    for i, var in enumerate(profile_vars):
        var_sub = sub[sub["variable"] == var].copy()
        if var_sub.empty:
            continue
        if var in ("occupation", "religion", "life_goals", "top_driver", "top_barrier"):
            var_sub["value"] = var_sub["value"].apply(lambda x: tr(_strip_hausa(x)))
        if set(var_sub["value"].tolist()) == {"mean"}:
            val = var_sub["proportion"].iloc[0]
            cols[i % 2].metric(_var_label(var), f"{val:.1f}")
        else:
            s = var_sub.set_index("value")["proportion"].sort_values(ascending=False)
            with cols[i % 2]:
                _hbar(s, _var_label(var),
                      key=f"persona_{key_suffix}_{persona_id}_{var}")


def render_comparison(df_profile, n_personas, split_label=None):
    key_suffix = split_label.replace(" ", "_").replace("/", "") if split_label else "overall"
    st.subheader("Persona comparison")
    st.caption("Compare the distribution of one variable across all personas.")

    profile_vars = [v for v in df_profile["variable"].unique() if not v.startswith("_")]
    selected_var = st.selectbox(
        "Select variable", profile_vars,
        format_func=_var_label,
        key=f"persona_compare_var_{key_suffix}",
    )

    sub = df_profile[df_profile["variable"] == selected_var].copy()
    if selected_var in ("occupation", "religion", "life_goals", "top_driver", "top_barrier"):
        sub["value"] = sub["value"].apply(lambda x: tr(_strip_hausa(x)))

    if set(sub["value"].tolist()) == {"mean"}:
        st.info("Comparison chart not available for numeric variables.")
        return

    traces = []
    for i, pid in enumerate(range(n_personas)):
        pdata = sub[sub["persona"] == pid].set_index("value")["proportion"]
        traces.append(go.Bar(
            name=f"Persona {pid}",
            x=pdata.index.astype(str),
            y=pdata.values,
            marker_color=FEM_PALETTE[i % len(FEM_PALETTE)],
            text=[f"{v*100:.0f}%" for v in pdata.values],
            textposition="outside",
        ))

    if not traces:
        return

    fig = go.Figure(traces)
    fig.update_layout(
        barmode="group",
        yaxis=dict(tickformat=".0%", showgrid=False, title="% of persona"),
        xaxis=dict(showgrid=False, tickangle=-30),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20, b=80, l=10, r=10),
        height=360,
        legend_title="Persona",
    )
    st.plotly_chart(fig, use_container_width=True, key=f"persona_compare_{key_suffix}")


# ── Standalone culture clustering ────────────────────────────────────────────
# 2026-09-02: a separate analysis from the persona splits above -- tests
# "do respondents geographically cluster based on their culture?" by
# clustering on religion, life goals, and top driver/barrier ONLY (region is
# excluded from the clustering inputs), then checking whether the resulting
# clusters concentrate in particular regions. If region were used as a
# clustering input instead, "clusters differ by region" would be true by
# construction rather than a real finding -- see CULTURE_CLUSTERING_VARS's
# comment in pipeline/config.py.

def render_culture_clusters():
    df_centroids = load_culture_clusters_centroids()
    df_profile = load_culture_clusters_profile()
    df_elbow = load_culture_clusters_elbow()

    st.subheader("Do cultural traits geographically cluster?")
    st.caption(
        "A separate analysis from the personas above: clusters respondents by "
        "**religion, life goals, and their top driver/barrier only** — region is "
        "deliberately left out of the clustering itself. The chart below then checks "
        "whether the resulting clusters are concentrated in particular regions, or "
        "spread evenly — that's the actual test of whether culture and geography line up."
    )

    if df_centroids is None or df_centroids.empty:
        st.warning(
            "Pre-aggregated culture-cluster data not found. "
            "Run `python -m pipeline.run_pipeline --pages personas` (from pipeline_output/) "
            "to generate it, then upload culture_clusters_centroids.csv / "
            "culture_clusters_profile.csv / culture_clusters_elbow.csv to Drive and "
            "wire the file IDs into src/data_loader.py."
        )
        return

    n_personas = df_centroids["persona"].nunique()

    if df_elbow is not None and not df_elbow.empty:
        with st.expander("Elbow plot — choosing number of clusters", expanded=False):
            render_elbow_plot(df_elbow, split_col="analysis", key="elbow_plot_culture")

    render_centroid_table(df_centroids, df_profile=df_profile, split_col="analysis")

    if df_profile is None or df_profile.empty:
        st.warning("Culture-cluster profile data not found.")
        return

    # ── The actual geography check: region mix per cluster ────────────────────
    region_rows = df_profile[df_profile["variable"] == "region"]
    if not region_rows.empty:
        st.markdown("**Region mix within each cluster**")
        st.caption(
            "If a cluster's bars pile up in one or two regions rather than spreading "
            "across all four, that cluster's cultural profile is geographically concentrated."
        )
        # x-axis = persona, one series per region (region composition within
        # each persona) -- swapped from region-on-x/persona-series per the
        # user's request, so you read across a persona to see its regional
        # makeup instead of across a region to see which personas live there.
        personas = list(range(n_personas))
        persona_labels = [f"Persona {p}" for p in personas]
        traces = []
        for i, region in enumerate(REGIONS):
            rdata = (
                region_rows[region_rows["value"] == region]
                .set_index("persona")["proportion"]
                .reindex(personas)
                .fillna(0)
            )
            traces.append(go.Bar(
                name=region,
                x=persona_labels,
                y=rdata.values,
                marker_color=FEM_PALETTE[i % len(FEM_PALETTE)],
                text=[f"{v*100:.0f}%" for v in rdata.values],
                textposition="outside",
            ))
        fig = go.Figure(traces)
        fig.update_layout(
            barmode="group",
            yaxis=dict(tickformat=".0%", showgrid=False, title="% of persona"),
            xaxis=dict(showgrid=False, title="Persona"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=40, l=10, r=10),
            height=340,
            legend_title="Region",
        )
        st.plotly_chart(fig, use_container_width=True, key="culture_region_mix")


def _render_split_tab(df_centroids_g, df_profile_g, split_label, split_col="gender"):
    n_personas = df_centroids_g["persona"].nunique()
    render_centroid_table(df_centroids_g, df_profile=df_profile_g, split_label=split_label, split_col=split_col)
    st.divider()
    if df_profile_g is not None and not df_profile_g.empty:
        tab1, tab2 = st.tabs(["Deep-dive", "Comparison"])
        with tab1:
            render_persona_profiles(df_profile_g, n_personas, split_label=split_label)
        with tab2:
            render_comparison(df_profile_g, n_personas, split_label=split_label)
    else:
        st.warning(f"Persona profile data not found for this {split_col}.")


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    st.header("Personas")
    st.caption(
        "We develop cluster-based respondent profiles (i.e. archetypes) based on the "
        "profiles of formative research participants. This approach is used in "
        "user-centred design and marketing to create representative \"customer personas\" "
        "that help teams empathise with their target audience and make informed design decisions."
    )
    st.markdown("""
### Methodology
Personas were derived using **k-modes clustering**, a variant of k-means adapted for
categorical data. Unlike k-means, k-modes uses modes (most frequent values) rather than
means as cluster centres, and measures dissimilarity by the number of mismatching
categories between observations — making it well-suited to survey responses.

**Clustering is run separately within each group of a split** (gender, or region) so
that within-group variation drives the clusters rather than the split variable itself.

**Clustering variables:** age, occupation, religion, life goals, top driver (main reason
for using contraception, among users), and top barrier (main reason for not using, among
non-users) — plus gender itself, when splitting by region, since gender isn't dropped there
the way it is for the gender split.

**Configuration:** initialised using the Cao method (which selects starting centroids
based on category frequency distributions to reduce sensitivity to random starting
points), with 5 independent runs to improve stability. Results are fully reproducible
(fixed random seed). The gender split and overall clustering use a fixed 3 clusters;
region splits (both 4-way and North/South) instead auto-select k per region from that
region's own elbow curve (2 vs. 3+ clusters is a real difference between regions, not
just noise — see the elbow plot below).

**Output:** Each persona represents the modal respondent within a cluster — the
combination of attribute values that best characterises that group. Cluster size (N and
weighted N) is shown for each persona. Individual-level data is not stored or displayed.
    """)
    st.markdown("")

    st.subheader("Personas by group")

    # ── Split selector: gender or separately sampled survey region ────────────
    split_choice = st.radio(
        "Split personas by",
        ["Gender", "Region"],
        horizontal=True,
    )
    split_col = {
        "Gender": "gender",
        "Region": "region",
    }[split_choice]

    if split_col == "gender":
        df_centroids_s = load_personas_centroids_by_gender()
        df_profile_s   = load_personas_profile_by_gender()
        df_elbow       = load_personas_elbow()
        label_map      = GENDER_DISPLAY
        missing_msg    = _MISSING
        region_order   = None
    elif split_col == "region":
        df_centroids_s = load_personas_centroids_by_region()
        df_profile_s   = load_personas_profile_by_region()
        df_elbow       = load_personas_elbow_by_region()
        label_map      = {}
        region_order   = REGIONS
        missing_msg = (
            "Pre-aggregated region-split persona data not found. "
            "Run `python -m pipeline.run_pipeline --pages personas` (from pipeline_output/) "
            "to generate it, then upload personas_centroids_by_region.csv / "
            "personas_profile_by_region.csv / personas_elbow_by_region.csv to Drive and "
            "wire the file IDs into src/data_loader.py."
        )
    if df_centroids_s is None or df_centroids_s.empty:
        st.warning(missing_msg)
        return

    # ── Elbow plot ────────────────────────────────────────────────────────────
    if df_elbow is not None and not df_elbow.empty:
        with st.expander("Elbow plot — choosing number of clusters", expanded=False):
            render_elbow_plot(df_elbow, split_col=split_col, key=f"elbow_plot_{split_col}")

    # ── Split tabs ────────────────────────────────────────────────────────────
    groups_in_data = df_centroids_s[split_col].unique().tolist()
    if region_order:
        # Prefer the canonical region order over whatever order they appear
        # in the data (North-East/North-West/South-South/Mid-South, or
        # North/South).
        groups_in_data = [g for g in region_order if g in groups_in_data] + \
                         [g for g in groups_in_data if g not in region_order]
    tab_labels = [tr(label_map.get(g, g)) for g in groups_in_data]
    tabs = st.tabs(tab_labels)

    for tab, group_label in zip(tabs, groups_in_data):
        with tab:
            c_sub = df_centroids_s[df_centroids_s[split_col] == group_label].copy()
            p_sub = (
                df_profile_s[df_profile_s[split_col] == group_label].copy()
                if df_profile_s is not None else None
            )
            _render_split_tab(c_sub, p_sub, group_label, split_col=split_col)

    # Standalone culture-clustering analysis -- moved to the end of the page
    # (2026-09-02, was above the split selector) since it's a separate
    # analysis from the persona splits above, not another view of the same
    # thing.
    st.divider()
    render_culture_clusters()
