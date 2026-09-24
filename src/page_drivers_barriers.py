"""
page_drivers_barriers.py  —  improved version
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from src.data_loader import (
    load_drivers_barriers, parse_subgroup_prevalence,
    parse_statements, get_priority_sort_key,
    USER_CATEGORY_LABELS, AGE_GROUPS, GENDERS,
)
from src.fem_colours import PRIORITY_COLORS, FEM_PALETTE
from src.translations import tr


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_hausa(text: str) -> str:
    """Return only the French part of a bilingual 'French/Fon' label (Benin's
    order -- first segment, not last)."""
    if "/" in str(text):
        french = str(text).split("/", 1)[0].strip()
        return french if french else str(text).strip()
    return str(text).strip()


def render_priority_badge(priority):
    color = PRIORITY_COLORS.get(str(priority).strip(), "#6b7280")
    return (
        f'<span style="background:{color};color:white;padding:2px 10px;'
        f'border-radius:12px;font-size:12px;font-weight:600;">{priority}</span>'
    )


def _overall_prevalence(row):
    """Best-effort: return a single numeric overall prevalence (0-100) for a row."""
    for col in ["Overall prevalence", "Prevalence overall", "overall", "Overall"]:
        if col in row.index and pd.notna(row[col]):
            try:
                return float(str(row[col]).replace("%", "").strip())
            except ValueError:
                pass
    # fall back: average the user-category subgroup values
    data = parse_subgroup_prevalence(row.get("Prevalence (All)", ""))
    if data:
        return sum(data.values()) / len(data)
    return None


def build_overview_chart(df, db_type, split_key="user_category", metric="prevalence"):
    """
    Consolidated grouped horizontal bar chart showing ALL drivers/barriers.
    metric: "prevalence" | "raw_n" | "weighted_n"
    """
    # ── Column maps ────────────────────────────────────────────────────────
    PREV_COL_MAP = {
        "user_category": "Prevalence (All)",
        "gender":        "GENDER: Prevalence (All)",
        "age":           "AGE_GROUP: Prevalence (All)",
        "region":        "REGION: Prevalence (All)",
    }
    RAW_N_COL_MAP = {
        "user_category": "N (All)",
        "gender":        "GENDER: N (All)",
        "age":           "AGE_GROUP: N (All)",
        "region":        "REGION: N (All)",
    }
    WGT_N_COL_MAP = {
        "user_category": "Weighted N (All)",
        "gender":        "GENDER: Weighted N (All)",
        "age":           "AGE_GROUP: Weighted N (All)",
        "region":        "REGION: Weighted N (All)",
    }
    UNWGT_PREV_COL_MAP = {
        "user_category": "Unweighted Prevalence (All)",
        "gender":        "GENDER: Unweighted Prevalence (All)",
        "age":           "AGE_GROUP: Unweighted Prevalence (All)",
        # No "REGION: Unweighted Prevalence (All)" column exists (same as urban_rural) --
        # falls back to regular prevalence automatically, see build_prevalence_bar below.
    }
    prev_col = PREV_COL_MAP.get(split_key, "Prevalence (All)")
    data_col = {
        "prevalence":            prev_col,
        "raw_n":                 RAW_N_COL_MAP.get(split_key, "N (All)"),
        "weighted_n":            WGT_N_COL_MAP.get(split_key, "Weighted N (All)"),
        "unweighted_prevalence": UNWGT_PREV_COL_MAP.get(split_key, "Unweighted Prevalence (All)"),
    }.get(metric, prev_col)

    records = []
    for _, row in df.iterrows():
        data = parse_subgroup_prevalence(row.get(data_col, ""))
        if not data and metric != "prevalence":
            # count column not yet in data — fall back to prevalence
            data = parse_subgroup_prevalence(row.get(prev_col, ""))
        if not data:
            # fallback: try the user_category column
            data = parse_subgroup_prevalence(row.get("Prevalence (All)", ""))
        if not data:
            # last resort: single bar from averaged value
            avg = _overall_prevalence(row)
            data = {"Overall": avg} if avg is not None else {}

        # Apply human-readable labels for user categories
        if split_key == "user_category":
            data = {USER_CATEGORY_LABELS.get(k, k): v for k, v in data.items()}
        else:
            # gender/age/region/urban_rural subgroup names -- translate raw
            # gender values ("Femme Nyɔnu"/"Homme Sunnu") when English is on;
            # tr() is a no-op for anything not in its lookup (age/region/urban_rural).
            data = {tr(k): v for k, v in data.items()}

        name     = tr(_strip_hausa(str(row["Name"])))
        priority = str(row["Priority"]).strip()
        max_prev = max(data.values()) if data else 0
        records.append({
            "name":     name,
            "priority": priority,
            "_sort":    get_priority_sort_key(priority),
            "max_prev": max_prev,
            "data":     data,
        })

    if not records:
        return go.Figure()

    # ── Sort: priority high→low, then prevalence high→low within band ──────
    plot_df = (
        pd.DataFrame(records)
        .sort_values(["_sort", "max_prev"], ascending=[False, False])
        .reset_index(drop=True)
    )

    # ── Collect all subgroup keys in a stable order ────────────────────────
    all_groups: list[str] = []
    for data in plot_df["data"]:
        for k in data:
            if k not in all_groups:
                all_groups.append(k)

    # Colours per subgroup — use the FEM palette; cycle if >5 groups
    group_colors = {g: FEM_PALETTE[i % len(FEM_PALETTE)] for i, g in enumerate(all_groups)}

    item_names = plot_df["name"].tolist()
    priority_of = dict(zip(plot_df["name"], plot_df["priority"]))

    # ── One trace per subgroup ─────────────────────────────────────────────
    is_counts = metric in ("raw_n", "weighted_n")
    is_pct    = metric in ("prevalence", "unweighted_prevalence")
    traces = []
    for grp in all_groups:
        x_vals = [row_data.get(grp, None) for row_data in plot_df["data"]]
        if is_counts:
            text_vals = [f"{int(v):,}" if v is not None else "" for v in x_vals]
            hover = "<b>%{y}</b><br>" + grp + ": %{x:,}<br>Priority: %{customdata}<extra></extra>"
        else:  # prevalence or unweighted_prevalence
            text_vals = [f"{v:.1f}%" if v is not None else "" for v in x_vals]
            hover = "<b>%{y}</b><br>" + grp + ": %{x:.1f}%<br>Priority: %{customdata}<extra></extra>"
        traces.append(go.Bar(
            name=grp,
            y=item_names,
            x=x_vals,
            orientation="h",
            marker_color=group_colors[grp],
            text=text_vals,
            textposition="outside",
            cliponaxis=False,
            hovertemplate=hover,
            customdata=[priority_of[n] for n in item_names],
        ))

    fig = go.Figure(traces)

    # ── Priority band dividers (subtle horizontal lines between bands) ─────
    # Find y-positions where priority changes
    priorities = plot_df["priority"].tolist()
    divider_positions = []
    for i in range(1, len(priorities)):
        if get_priority_sort_key(priorities[i]) != get_priority_sort_key(priorities[i - 1]):
            divider_positions.append(i - 0.5)

    shapes = [
        dict(
            type="line",
            x0=0, x1=1, xref="paper",
            y0=pos, y1=pos, yref="y",
            line=dict(color="#cccccc", width=1, dash="dot"),
        )
        for pos in divider_positions
    ]

    # ── Priority band annotations on the right margin ─────────────────────
    # Label the first item in each band
    annotations = []
    seen_priorities = set()
    for i, row in plot_df.iterrows():
        p = row["priority"]
        if p not in seen_priorities:
            seen_priorities.add(p)
            color = PRIORITY_COLORS.get(p, "#6b7280")
            annotations.append(dict(
                x=1.01, xref="paper",
                y=row["name"], yref="y",
                text=f"<b>{p}</b>",
                showarrow=False,
                xanchor="left",
                font=dict(color=color, size=12),
            ))

    max_x = max(
        (v for d in plot_df["data"] for v in d.values() if v is not None),
        default=10,
    )

    metric_labels = {"prevalence": "prevalence", "raw_n": "raw n", "weighted_n": "weighted n", "unweighted_prevalence": "unweighted prevalence"}
    axis_titles   = {"prevalence": "% of respondents", "raw_n": "Respondents (n)", "weighted_n": "Weighted respondents", "unweighted_prevalence": "% of respondents (unweighted)"}
    fig.update_layout(
        title=f"All {db_type}s — {metric_labels.get(metric, 'prevalence')} by {split_key.replace('_', ' ')}",
        barmode="group",
        xaxis=dict(
            title=axis_titles.get(metric, "% of respondents"),
            showgrid=False,
            range=[0, max_x * 1.4],
        ),
        yaxis=dict(showgrid=False, autorange="reversed"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=280, r=180, t=80, b=10),
        height=max(500, len(plot_df) * 52 + 100),
        legend=dict(
            title=dict(text=split_key.replace("_", " ").title(), side="left"),
            orientation="h",
            x=0, y=1.06,
            xanchor="left",
            yanchor="bottom",
            bgcolor="rgba(0,0,0,0)",
        ),
        shapes=shapes,
        annotations=annotations,
        showlegend=True,
        font=dict(size=14),
    )
    return fig


def build_prevalence_bar(row, split="user_category", metric="prevalence"):
    """
    Build a single bar chart for one driver/barrier.
    metric: "prevalence" | "raw_n" | "weighted_n"
    """
    PREV_COL = {
        "user_category": "Prevalence (All)",
        "gender":        "GENDER: Prevalence (All)",
        "age":           "AGE_GROUP: Prevalence (All)",
        "region":        "REGION: Prevalence (All)",
    }
    RAW_N_COL = {
        "user_category": "N (All)",
        "gender":        "GENDER: N (All)",
        "age":           "AGE_GROUP: N (All)",
        "region":        "REGION: N (All)",
    }
    WGT_N_COL = {
        "user_category": "Weighted N (All)",
        "gender":        "GENDER: Weighted N (All)",
        "age":           "AGE_GROUP: Weighted N (All)",
        "region":        "REGION: Weighted N (All)",
    }
    UNWGT_PREV_COL = {
        "user_category": "Unweighted Prevalence (All)",
        "gender":        "GENDER: Unweighted Prevalence (All)",
        "age":           "AGE_GROUP: Unweighted Prevalence (All)",
        # No REGION equivalent -- see build_overview_chart's UNWGT_PREV_COL_MAP note.
    }

    prev_col = PREV_COL.get(split)
    if not prev_col:
        return None

    # Prevalence data is always needed for labels / fallback
    prev_data = parse_subgroup_prevalence(row.get(prev_col, ""))
    if not prev_data:
        return None

    if split == "user_category":
        labels = [USER_CATEGORY_LABELS.get(k, k) for k in prev_data]
    else:
        labels = [tr(k) for k in prev_data]

    # ── Unweighted prevalence % ───────────────────────────────────────────────
    if metric == "unweighted_prevalence":
        unwgt_col  = UNWGT_PREV_COL.get(split)
        unwgt_data = parse_subgroup_prevalence(row.get(unwgt_col, "")) if unwgt_col else {}
        if not unwgt_data:
            return build_prevalence_bar(row, split, metric="prevalence")
        if split == "user_category":
            u_labels = [USER_CATEGORY_LABELS.get(k, k) for k in unwgt_data]
        else:
            u_labels = [tr(k) for k in unwgt_data]
        u_values = list(unwgt_data.values())
        fig = go.Figure(go.Bar(
            x=u_values,
            y=u_labels,
            orientation="h",
            marker_color=FEM_PALETTE[:len(u_labels)],
            text=[f"{v:.1f}%" for v in u_values],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
        ))
        fig.update_layout(
            margin=dict(l=0, r=60, t=4, b=4),
            height=max(80, len(u_labels) * 36),
            xaxis=dict(
                range=[0, max(u_values) * 1.35],
                showticklabels=False,
                showgrid=False,
                zeroline=False,
                title="% of respondents (unweighted)",
            ),
            yaxis=dict(showgrid=False),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            font=dict(size=12),
        )
        return fig

    # ── Counts ────────────────────────────────────────────────────────────────
    if metric in ("raw_n", "weighted_n"):
        count_col = (RAW_N_COL if metric == "raw_n" else WGT_N_COL).get(split)
        count_data = parse_subgroup_prevalence(row.get(count_col, "")) if count_col else {}

        if not count_data:
            # column not in data yet — fall back to prevalence
            return build_prevalence_bar(row, split, metric="prevalence")

        if split == "user_category":
            c_labels = [USER_CATEGORY_LABELS.get(k, k) for k in count_data]
        else:
            c_labels = [tr(k) for k in count_data]
        c_values = list(count_data.values())

        color     = FEM_PALETTE[0] if metric == "raw_n" else FEM_PALETTE[2]
        text_vals = [f"{int(v):,}" for v in c_values] if metric == "raw_n" else [f"{v:,.1f}" for v in c_values]
        x_title   = "Respondents (n)" if metric == "raw_n" else "Weighted respondents"

        fig = go.Figure(go.Bar(
            x=c_values,
            y=c_labels,
            orientation="h",
            marker_color=color,
            text=text_vals,
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x:,}<extra></extra>",
        ))
        fig.update_layout(
            margin=dict(l=0, r=80, t=4, b=4),
            height=max(80, len(c_labels) * 36),
            xaxis=dict(range=[0, max(c_values) * 1.35], showgrid=False,
                       showticklabels=False, zeroline=False, title=x_title),
            yaxis=dict(showgrid=False),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            font=dict(size=12),
        )
        return fig

    # ── Prevalence % ──────────────────────────────────────────────────────────
    values = list(prev_data.values())
    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker_color=FEM_PALETTE[:len(labels)],
        text=[f"{v:.1f}%" for v in values],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(l=0, r=60, t=4, b=4),
        height=max(80, len(labels) * 36),
        xaxis=dict(
            range=[0, max(values) * 1.35],
            showticklabels=False,
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(showgrid=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(size=12),
    )
    return fig


def build_statement_chart(row, split="user_category"):
    if split == "user_category":
        stmt, pcts = parse_statements(row["Statements"])
    elif split == "gender":
        stmt, pcts = parse_statements(row["GENDER: Statements"])
    elif split == "age":
        stmt, pcts = parse_statements(row["AGE_GROUP: Statements"])
    elif split == "region":
        stmt, pcts = parse_statements(row["REGION: Statements"])
    else:
        return None, None

    if not pcts:
        return stmt, None

    labels = list(pcts.keys())
    values = list(pcts.values())

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker_color=FEM_PALETTE[:len(labels)],
        text=[f"{v:.0f}%" for v in values],
        textposition="outside",
        cliponaxis=False,
    ))
    fig.update_layout(
        margin=dict(l=0, r=60, t=4, b=4),
        height=max(80, len(labels) * 36),
        xaxis=dict(range=[0, 115], showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showgrid=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(size=12),
    )
    return stmt, fig


# ── Main render ───────────────────────────────────────────────────────────────

def render(df_raw=None):
    st.header("Drivers & Barriers")
    st.caption(
        "Drivers are factors that motivate or facilitate contraceptive use. "
        "Barriers are factors that prevent or discourage it. "
        "Each item is coded from qualitative responses and assigned a priority level "
        "based on how frequently it was mentioned and its assessed importance."
    )
    st.markdown("""
### Methodology
Drivers and barriers were identified through **thematic analysis** of open-ended survey
responses. Each item was coded by trained analysts and reviewed for consistency. Prevalence
reflects the share of respondents who mentioned a given driver or barrier as one of their
main reasons for using or not using contraception.

**Priority levels** reflect a combination of prevalence and strategic importance:
- **Very high** — mentioned by a large share of respondents and/or considered a critical lever for behaviour change
- **High** — frequently mentioned and actionable
- **Medium** — moderately prevalent; worth addressing in programme design
- **Low** — less common; may be relevant for specific sub-groups

**Subgroup breakdowns** (user category, gender, age group, region) show the prevalence of
each item within that subgroup. Weighted prevalence uses post-stratification survey weights
to account for differences in sampling across regions and demographics.

**Belief-statement agreement** (shown in detail cards below) is only available for
**barriers**, not drivers: the 62 belief statements were all written to test barrier-side
beliefs (cost, side effects, religion, family approval, fertility desire) — none have a
driver-side counterpart, so driver items intentionally show no statement chart.
    """)
    st.markdown("")

    if df_raw is None:
        df_raw = load_drivers_barriers()

    # ── Controls ──────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns([0.7, 1.0, 1.4, 0.8], gap="medium")
    with col1:
        db_type = st.radio("Show", ["Driver", "Barrier"], horizontal=True)
    with col2:
        split_by = st.radio(
            "Split by", ["User category", "Gender", "Age group", "Region"], horizontal=True
        )
    with col3:
        priority_filter = st.multiselect(
            "Priority filter",
            ["Very high", "High", "Medium", "Low"],
            default=["Very high", "High", "Medium", "Low"],
        )
    with col4:
        metric_choice = st.selectbox(
            "Metric",
            ["Prevalence (%)", "Unweighted prevalence (%)", "Raw n", "Weighted n"],
            help=(
                "Prevalence: weighted % of respondents who mentioned this item. "
                "Unweighted prevalence: same but without survey weights applied. "
                "Raw n: unweighted respondent count. "
                "Weighted n: effective sample size after survey weights."
            ),
        )
    metric = {
        "Prevalence (%)":            "prevalence",
        "Unweighted prevalence (%)": "unweighted_prevalence",
        "Raw n":                     "raw_n",
        "Weighted n":                "weighted_n",
    }[metric_choice]

    split_key = {
        "User category": "user_category",
        "Gender":        "gender",
        "Age group":     "age",
        "Region":        "region",
    }[split_by]

    # ── Filter ────────────────────────────────────────────────────────────────
    df = df_raw[df_raw["Driver/Barrier"].str.lower() == db_type.lower()].copy()
    if priority_filter:
        df = df[df["Priority"].isin(priority_filter)]
    df["_sort"] = df["Priority"].apply(get_priority_sort_key)
    df = df.sort_values("_sort", ascending=False).reset_index(drop=True)

    if df.empty:
        st.info("No data matches the current filters.")
        return

    # ── Overview chart ────────────────────────────────────────────────────────
    st.markdown("### Overview — all items at a glance")
    st.caption(
        "Bars coloured by priority level. "
        "Prevalence = % of respondents who mentioned this as a main driver/barrier."
    )
    st.plotly_chart(
        build_overview_chart(df, db_type, split_key=split_key, metric=metric),
        use_container_width=True,
        key="overview_chart",
    )

    # ── Detail cards (collapsible section) ───────────────────────────────────
    with st.expander(f"Detail cards — {len(df)} main {db_type.lower()}(s)", expanded=False):
        st.caption("Sorted by priority, then by prevalence. Click any item to expand.")

        for card_idx, (_, row) in enumerate(df.iterrows()):
            name_raw = str(row["Name"])
            name     = tr(_strip_hausa(name_raw))
            priority = str(row["Priority"]).strip()

            badge_color    = PRIORITY_COLORS.get(priority, "#6b7280")
            expander_label = f"**{name}**  —  {priority}"

            with st.expander(expander_label, expanded=False):
                st.markdown(
                    f'<span style="background:{badge_color};color:white;padding:2px 10px;'
                    f'border-radius:12px;font-size:12px;font-weight:600;">'
                    f'{priority} priority — main {db_type.lower()}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown("")

                fig_prev = build_prevalence_bar(row, split_key, metric=metric)
                if fig_prev:
                    card_label = {
                        "prevalence":            "*Prevalence — % of respondents who mentioned this (weighted)*",
                        "unweighted_prevalence": "*Unweighted prevalence — % of respondents who mentioned this*",
                        "raw_n":                 "*Respondent counts (unweighted n)*",
                        "weighted_n":            "*Weighted respondent counts*",
                    }.get(metric, "")
                    st.markdown(card_label)
                    st.plotly_chart(
                        fig_prev, use_container_width=True,
                        key=f"prev_{card_idx}",
                    )

                stmt, fig_stmt = build_statement_chart(row, split_key)
                if fig_stmt:
                    stmt_text = tr(stmt) if stmt else "Related belief statement"
                    st.markdown(f"*Agreement with: \"{stmt_text}\"*")
                    st.plotly_chart(
                        fig_stmt, use_container_width=True,
                        key=f"stmt_{card_idx}",
                    )
                elif db_type == "Driver":
                    # Not missing data -- the 62 belief statements were all written to test
                    # barrier-side beliefs (cost, side effects, religion, family approval,
                    # fertility-desire), so no driver reason has a matching statement to
                    # show agreement for. Confirmed with the user (2026-08-24) rather than
                    # left silently blank, so this doesn't read as a bug to the next viewer.
                    st.caption(
                        "No belief-statement data for this item — the statement bank tests "
                        "barrier-side beliefs only, with no driver-side counterpart."
                    )

                if not fig_prev and not fig_stmt and db_type != "Driver":
                    st.info("No chart data available for this item.")
