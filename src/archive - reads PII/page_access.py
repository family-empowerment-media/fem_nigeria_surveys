import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from src.fem_colours import FEM_ORANGE, FEM_BROWN, FEM_TAUPE, FEM_STEEL, FEM_NAVY, FEM_SCALE
from src.data_loader import load_raw_data

# ── Constants ─────────────────────────────────────────────────────────────────

USER_GROUPS    = ["user", "past_user"]
NONUSER_GROUPS = ["non_user", "future_user"]

WTT_MAP = {
    "0-5 minutes":    2.5,
    "5-15 minutes":   10,
    "15-30 minutes":  22.5,
    "30-45 minutes":  37.5,
    "45-60 minutes":  52.5,
    "60-90 minutes":  75,
    "90-120 minutes": 105,
    "2-3 hours":      150,
    "3-4 hours":      210,
    "4+ hours":       270,
}

WEIGHT_COL = "combined_weight_adjusted"

SPLIT_MAP = {
    "User group": "use",
    "Gender":     "gender",
    "Age group":  "age_group",
}

FEM_PALETTE = [FEM_ORANGE, FEM_BROWN, FEM_TAUPE, FEM_STEEL, FEM_NAVY]

# ── Helpers ───────────────────────────────────────────────────────────────────

def weighted_prop(df, col, weight=WEIGHT_COL):
    """Weighted proportion for a boolean/binary column."""
    valid = df[[col, weight]].dropna()
    if valid.empty or valid[weight].sum() == 0:
        return np.nan
    return (valid[col] * valid[weight]).sum() / valid[weight].sum()


def weighted_mean(df, col, weight=WEIGHT_COL):
    valid = df[[col, weight]].dropna()
    if valid.empty or valid[weight].sum() == 0:
        return np.nan
    return (valid[col] * valid[weight]).sum() / valid[weight].sum()


def split_weighted_prop(df, bool_col, split_col, weight=WEIGHT_COL):
    """Return a Series of weighted proportions by split_col groups."""
    result = {}
    for grp, gdf in df.groupby(split_col):
        result[grp] = weighted_prop(gdf, bool_col, weight)
    return pd.Series(result).dropna()


def split_weighted_mean(df, num_col, split_col, weight=WEIGHT_COL):
    result = {}
    for grp, gdf in df.groupby(split_col):
        result[grp] = weighted_mean(gdf, num_col, weight)
    return pd.Series(result).dropna()


def simple_bar(series, title, x_label, y_label, pct=True, palette=None):
    """Horizontal bar chart from a Series."""
    if series.empty:
        return None
    colors = (palette or FEM_PALETTE) * (len(series) // len(FEM_PALETTE) + 1)
    text = [f"{v*100:.1f}%" if pct else f"{v:.1f}" for v in series]
    fig = go.Figure(go.Bar(
        y=series.index.astype(str),
        x=series.values,
        orientation="h",
        marker_color=colors[:len(series)],
        text=text,
        textposition="outside",
        cliponaxis=False,
    ))
    fig.update_layout(
        title=title,
        xaxis=dict(
            title=x_label,
            tickformat=".0%" if pct else "",
            showgrid=False,
            range=[0, series.max() * 1.3 if pct else series.max() * 1.2],
        ),
        yaxis=dict(title=y_label, showgrid=False, autorange="reversed"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=60, t=40, b=30),
        height=max(200, len(series) * 44 + 80),
        showlegend=False,
    )
    return fig


def other_responses_table(df, response_col, other_col, label):
    """
    Replace -88 coded responses with the free-text 'other' answer,
    then return a value-count table.
    """
    combined = df[response_col].copy()
    mask = combined == -88
    combined.loc[mask] = df.loc[mask, other_col]
    counts = combined.dropna().value_counts().reset_index()
    counts.columns = [label, "Count"]
    return counts


# ── Section renderers ─────────────────────────────────────────────────────────

def render_availability(df, split_col):
    st.subheader("1. Availability")
    st.caption(
        "Are contraceptives stocked when people seek them? "
        "Users and non-users were asked separate questions."
    )

    users    = df[df["use"].isin(USER_GROUPS)].copy()
    nonusers = df[df["use"].isin(NONUSER_GROUPS)].copy()

    col1, col2 = st.columns(2)

    # ── Users: stockout rate ──────────────────────────────────────────────────
    with col1:
        st.markdown("**Users & past users**")
        if "stockouts_users" in df.columns:
            users["_stockout"] = users["stockouts_users"].str.lower().str.contains("yes", na=False)
            rate = split_weighted_prop(users, "_stockout", split_col)
            fig = simple_bar(rate, "Stockout rate", "Proportion reporting stockout", split_col)
            if fig:
                st.plotly_chart(fig, use_container_width=True, key="avail_users")
        else:
            st.info("Column `stockouts_users` not found.")

        # Responses to stockouts
        if "stockouts_response" in df.columns and "stockouts_response_other" in df.columns:
            with st.expander("How did users respond to stockouts?"):
                tbl = other_responses_table(
                    users.dropna(subset=["stockouts_response"]),
                    "stockouts_response",
                    "stockouts_response_other",
                    "Response",
                )
                st.dataframe(tbl, use_container_width=True, hide_index=True)

    # ── Non-users: sought contraceptives + stockout rate ─────────────────────
    with col2:
        st.markdown("**Non-users & future users**")
        if "nonusers_seek_contraceptives" in df.columns:
            nonusers["_sought"] = nonusers["nonusers_seek_contraceptives"].str.lower().str.contains("yes", na=False)
            sought_rate = split_weighted_prop(nonusers, "_sought", split_col)
            fig2 = simple_bar(sought_rate, "Sought contraceptives", "Proportion who sought", split_col)
            if fig2:
                st.plotly_chart(fig2, use_container_width=True, key="avail_sought")

        if "stockouts_nonusers" in df.columns:
            # Denominator: only those who sought contraceptives
            sought = nonusers[nonusers.get("_sought", pd.Series(False, index=nonusers.index))]
            sought["_stockout"] = sought["stockouts_nonusers"].str.lower().str.contains("yes", na=False)
            rate2 = split_weighted_prop(sought, "_stockout", split_col)
            fig3 = simple_bar(rate2, "Stockout rate (among those who sought)", "Proportion", split_col)
            if fig3:
                st.plotly_chart(fig3, use_container_width=True, key="avail_nonusers")

        if "stockouts_nonusers_response" in df.columns and "stockouts_nonusers_response_other" in df.columns:
            with st.expander("How did non-users respond to stockouts?"):
                tbl2 = other_responses_table(
                    nonusers.dropna(subset=["stockouts_nonusers_response"]),
                    "stockouts_nonusers_response",
                    "stockouts_nonusers_response_other",
                    "Response",
                )
                st.dataframe(tbl2, use_container_width=True, hide_index=True)


def render_accessibility(df, split_col):
    st.subheader("2. Accessibility")
    st.caption("Travel time to facilities, willingness to travel, and the gap between them.")

    users    = df[df["use"].isin(USER_GROUPS)].copy()
    nonusers = df[df["use"].isin(NONUSER_GROUPS)].copy()

    # Willingness to travel (asked to all)
    if "willingness_to_travel" in df.columns:
        df = df.copy()
        df["wtt_minutes"] = df["willingness_to_travel"].map(WTT_MAP)

    # ── Mean travel times ─────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        if "travel_time_users" in users.columns:
            means = split_weighted_mean(users, "travel_time_users", split_col)
            fig = simple_bar(means, "Mean travel time — users (mins)", "Minutes", split_col, pct=False)
            if fig:
                st.plotly_chart(fig, use_container_width=True, key="travel_users")

    with col2:
        if "travel_time_nonusers" in nonusers.columns:
            means2 = split_weighted_mean(nonusers, "travel_time_nonusers", split_col)
            fig2 = simple_bar(means2, "Mean travel time — non-users (mins)", "Minutes", split_col, pct=False)
            if fig2:
                st.plotly_chart(fig2, use_container_width=True, key="travel_nonusers")

    # ── Travel gap: actual vs. willing ────────────────────────────────────────
    st.markdown("**Travel time gap** — share of users travelling further than they are willing to")
    if "travel_time_users" in users.columns and "wtt_minutes" in df.columns:
        users_wtt = users.merge(df[["wtt_minutes"]], left_index=True, right_index=True, how="left")
        users_wtt["travel_gap"] = users_wtt["travel_time_users"] - users_wtt["wtt_minutes"]
        users_wtt["_barrier"] = users_wtt["travel_gap"] > 0

        overall_gap = weighted_prop(users_wtt, "_barrier")
        st.metric("Overall travel barrier rate (users)", f"{overall_gap*100:.1f}%" if not np.isnan(overall_gap) else "N/A")

        gap_by_split = split_weighted_prop(users_wtt, "_barrier", split_col)
        fig3 = simple_bar(gap_by_split, f"Travel barrier rate by {split_col}", "Proportion", split_col)
        if fig3:
            st.plotly_chart(fig3, use_container_width=True, key="travel_gap")

    # ── Transport modes ───────────────────────────────────────────────────────
    with st.expander("Transport modes"):
        c1, c2 = st.columns(2)
        for col_name, label, subset, ckey in [
            ("transport_mode_users",    "Users",     users,    "tm_u"),
            ("transport_mode_nonusers", "Non-users", nonusers, "tm_nu"),
        ]:
            if col_name in df.columns:
                counts = subset[col_name].value_counts(normalize=True).head(8)
                fig_t = simple_bar(counts, f"Transport mode — {label}", "Share", "Mode")
                if fig_t:
                    (c1 if ckey == "tm_u" else c2).plotly_chart(fig_t, use_container_width=True, key=ckey)


def render_affordability(df, split_col):
    st.subheader("3. Affordability")
    st.caption(
        "Cost of contraceptives for users/past users vs. "
        "expected cost of a health visit for non-users/future users."
    )

    users    = df[df["use"].isin(USER_GROUPS)].copy()
    nonusers = df[df["use"].isin(NONUSER_GROUPS)].copy()

    col1, col2 = st.columns(2)

    with col1:
        if "user_costs" in users.columns:
            means = split_weighted_mean(users, "user_costs", split_col)
            fig = simple_bar(means, "Mean contraceptive cost — users (CFA)", "CFA", split_col, pct=False)
            if fig:
                st.plotly_chart(fig, use_container_width=True, key="cost_users")

    with col2:
        if "nonuser_cost" in nonusers.columns:
            means2 = split_weighted_mean(nonusers, "nonuser_cost", split_col)
            fig2 = simple_bar(means2, "Expected health visit cost — non-users (CFA)", "CFA", split_col, pct=False)
            if fig2:
                st.plotly_chart(fig2, use_container_width=True, key="cost_nonusers")

    # Cost barrier: any cost > 0 is a barrier (as in notebook)
    if "user_costs" in users.columns:
        users["_cost_barrier"] = users["user_costs"] > 0
        overall = weighted_prop(users, "_cost_barrier")
        st.metric(
            "Share of users who paid anything for contraceptives",
            f"{overall*100:.1f}%" if not np.isnan(overall) else "N/A",
        )


def render_composite(df):
    st.subheader("4. Composite supply indicator")
    st.caption(
        "Each respondent is scored on three supply-side barriers. "
        "The composite shows what share face at least one barrier."
    )

    # Derive barrier flags
    df = df.copy()

    if "willingness_to_travel" in df.columns:
        df["wtt_minutes"] = df["willingness_to_travel"].map(WTT_MAP)

    users = df[df["use"].isin(USER_GROUPS)].copy()

    # Supply: stockout reported by user OR non-user
    df["supply_barrier"] = False
    if "stockouts_users" in df.columns:
        df["supply_barrier"] |= df["stockouts_users"].str.lower().str.contains("yes", na=False)
    if "stockouts_nonusers" in df.columns:
        df["supply_barrier"] |= df["stockouts_nonusers"].str.lower().str.contains("yes", na=False)

    # Geo barrier: travel time > willingness (users only; NaN -> False)
    df["geo_barrier"] = False
    if "travel_time_users" in df.columns and "wtt_minutes" in df.columns:
        df["geo_barrier"] = (df["travel_time_users"] - df["wtt_minutes"]).gt(0).fillna(False)

    # Cost barrier: paid anything
    df["cost_barrier"] = False
    if "user_costs" in df.columns:
        df["cost_barrier"] = df["user_costs"].gt(0).fillna(False)

    # Any barrier
    df["any_barrier"] = df["supply_barrier"] | df["geo_barrier"] | df["cost_barrier"]

    barrier_cols = {
        "Supply (stockout)": "supply_barrier",
        "Geographic (travel gap)": "geo_barrier",
        "Cost (paid > 0)": "cost_barrier",
        "Any barrier": "any_barrier",
    }

    rates = {
        label: weighted_prop(df, col)
        for label, col in barrier_cols.items()
    }
    rates_s = pd.Series(rates).dropna()

    # Grouped bar: overall rates
    fig = go.Figure(go.Bar(
        x=rates_s.index,
        y=rates_s.values,
        marker_color=FEM_PALETTE[:len(rates_s)],
        text=[f"{v*100:.1f}%" for v in rates_s.values],
        textposition="outside",
    ))
    fig.update_layout(
        title="Composite supply barrier rates",
        yaxis=dict(tickformat=".0%", title="Proportion", showgrid=False, range=[0, rates_s.max() * 1.3]),
        xaxis=dict(showgrid=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=40, b=20),
        height=320,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, key="composite")

    # Optional: breakdown by use group
    with st.expander("Barrier rates by user group"):
        rows = []
        for label, col in barrier_cols.items():
            for grp in ["user", "past_user", "future_user", "non_user"]:
                sub = df[df["use"] == grp]
                val = weighted_prop(sub, col)
                rows.append({"Barrier": label, "Group": grp, "Rate": val})
        breakdown = pd.DataFrame(rows).dropna(subset=["Rate"])
        if not breakdown.empty:
            fig2 = px.bar(
                breakdown,
                x="Barrier",
                y="Rate",
                color="Group",
                barmode="group",
                text=breakdown["Rate"].apply(lambda v: f"{v*100:.1f}%"),
                color_discrete_sequence=FEM_PALETTE,
            )
            fig2.update_layout(
                yaxis=dict(tickformat=".0%", title="Proportion", showgrid=False),
                xaxis=dict(showgrid=False),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                height=340,
                legend_title="User group",
            )
            st.plotly_chart(fig2, use_container_width=True, key="composite_grp")


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    st.title("Health Access Barriers")

    df = load_raw_data()

    # Global split selector
    split_by  = st.radio("Split all charts by", list(SPLIT_MAP.keys()), horizontal=True)
    split_col = SPLIT_MAP[split_by]

    st.divider()
    render_availability(df, split_col)
    st.divider()
    render_accessibility(df, split_col)
    st.divider()
    render_affordability(df, split_col)
    st.divider()
    render_composite(df)