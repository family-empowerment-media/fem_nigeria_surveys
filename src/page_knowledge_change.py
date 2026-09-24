"""Phone Pulse — Baseline vs Follow-up (formative <-> pulse linkage)."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from src.data_loader import load_knowledge_change, load_fp_use_change

FEM_ORANGE = "#C1693A"
FEM_NAVY   = "#2E3F52"
FEM_TAUPE  = "#7A7068"

_CHART = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
SIG_THRESHOLD = 0.05


def _pending(csv_name: str) -> None:
    st.info(
        f"Data pending: run `3_linkage/compare_fp_use.py`, upload `{csv_name}.csv` to "
        f"Drive with link sharing on, then paste its file ID into `data_loader.py`."
    )


def _footnotes(items: list[str]) -> None:
    """Render a small numbered "Sources" list — superscript markers in the
    surrounding text (¹ ² ³ …) refer to these in order."""
    st.caption("Sources:  " + "&nbsp;&nbsp;·&nbsp;&nbsp; ".join(
        f"{i+1}. {text}" for i, text in enumerate(items)
    ))


def _render_questions_asked(baseline_q: str, followup_q: str, sources: list[str]) -> None:
    with st.expander("Survey questions asked"):
        st.markdown(f"**Formative Research (baseline, in-person interview):**¹\n\n> {baseline_q}")
        st.markdown(f"**Phone Pulse (follow-up, phone call):**²\n\n> {followup_q}")
        st.caption(
            "The two surveys were run in different languages/modes and don't use "
            "identical wording — see the Limitations section below for what that "
            "can mean for comparability."
        )
        st.markdown("---")
        _footnotes(sources)


def _render_method_awareness() -> None:
    df = load_knowledge_change()

    overall = df[df["method"] == "__OVERALL__"]
    methods = df[df["method"] != "__OVERALL__"].sort_values("known_pulse_pct")

    st.caption(
        "Awareness of specific contraceptive methods, Formative Research "
        "baseline vs. Phone Pulse follow-up, for the SAME 471 respondents "
        "linked across both waves (not all 968 baseline respondents — see "
        "\"How this comparison works\" above)."
    )
    _render_questions_asked(
        "\"Which contraceptive methods are you familiar with?\" (English hint on the "
        "SurveyCTO form; asked in Hausa in the field) — **enumerator instruction: "
        "do NOT read the method list out loud; only record methods the respondent "
        "volunteers unprompted.** Only asked of respondents who'd already indicated "
        "they'd heard of birth spacing at all.",
        "\"I want you to think about methods you have heard of for delaying or "
        "avoiding pregnancies. Can you list all of the methods you know about for "
        "family planning?\" — **enumerator instruction: read each method and ask if "
        "the respondent has heard of it.** Asked of everyone.",
        sources=[
            "field `known_contraceptive_options`, `label`/`hint` columns — "
            "`1_formative_research/table_analysis/data/1_raw/Ha-Fr_Collecte de "
            "Données sur le Terrain.xlsx`, sheet `survey`.",
            "field `fpbeh_awarefp`, `label`/`hint` columns — `2_phone pulse/meta/"
            "Participants_Appels de Suivi.xlsx`, sheet `survey`.",
        ],
    )
    st.warning(
        "⚠️ **Not apples-to-apples**: baseline used unprompted (unaided) recall — "
        "the enumerator never read out the method list¹ — while follow-up used "
        "prompted (aided) recall — the enumerator read each method aloud and asked "
        "about it directly². Aided recall reliably produces higher \"known\" rates "
        "than unaided recall in survey methodology generally, independent of any "
        "real change in awareness. Some (possibly most) of the baseline-to-follow-up "
        "increase shown below could be this measurement artifact rather than the "
        "campaign."
    )
    st.caption(
        "¹ ² same form fields as \"Survey questions asked\" above — see that "
        "expander for the exact source citation."
    )
    st.markdown("---")

    if not overall.empty:
        row = overall.iloc[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("Known at baseline", f"{row['known_baseline_pct']:.0f}%")
        col2.metric(
            "Known at follow-up", f"{row['known_pulse_pct']:.0f}%",
            delta=f"{row['known_pulse_pct'] - row['known_baseline_pct']:+.0f} pts",
        )
        col3.metric("Respondents linked", str(int(row["gained_awareness_n"]) +
                                               int(row["lost_awareness_n"])) + "+ w/ change")
        st.caption(row.get("direction", ""))
        st.markdown("---")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=methods["known_baseline_pct"], y=methods["method"], orientation="h",
        name="Baseline", marker_color=FEM_TAUPE,
        text=methods["known_baseline_pct"].map(lambda v: f"{v:.0f}%"),
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        x=methods["known_pulse_pct"], y=methods["method"], orientation="h",
        name="Follow-up", marker_color=FEM_NAVY,
        text=methods["known_pulse_pct"].map(lambda v: f"{v:.0f}%"),
        textposition="outside",
    ))
    fig.update_layout(
        **_CHART,
        title="Method awareness: baseline vs. follow-up",
        barmode="group",
        xaxis_title="% of linked respondents aware of method",
        xaxis_range=[0, 115],
        height=max(300, 45 * len(methods) + 100),
        margin=dict(l=10, r=30, t=78, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.15, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

    sig = methods[methods["mcnemar_p_value"] < SIG_THRESHOLD]
    if not sig.empty:
        st.caption(
            f"Statistically significant change (McNemar's exact test, p < "
            f"{SIG_THRESHOLD}): " + ", ".join(sig["method"].tolist())
        )

    st.markdown("#### Detail")
    st.dataframe(
        methods[["method", "known_baseline_pct", "known_pulse_pct",
                 "gained_awareness_n", "lost_awareness_n",
                 "mcnemar_p_value", "direction"]]
        .rename(columns={
            "method": "Method", "known_baseline_pct": "Baseline %",
            "known_pulse_pct": "Follow-up %", "gained_awareness_n": "Gained (n)",
            "lost_awareness_n": "Lost (n)", "mcnemar_p_value": "p-value",
            "direction": "Direction",
        })
        .sort_values("p-value")
        .reset_index(drop=True),
        use_container_width=True, hide_index=True,
    )


def _render_fp_use() -> None:
    df = load_fp_use_change()
    if df is None:
        _pending("fp_use_change_summary")
        return
    if df.empty:
        st.info("No data available.")
        return

    st.caption(
        "Current FP use, Formative Research baseline vs. Phone Pulse follow-up, "
        "for the SAME 471 respondents linked across both waves (not all 968 "
        "baseline respondents — see \"How this comparison works\" above)."
    )
    _render_questions_asked(
        "\"In the last six months, have you used any methods of childbirth "
        "spacing?\" (English hint on the SurveyCTO form; asked in Hausa in the "
        "field). Only asked of respondents who indicated they'd ever used FP — "
        "skipped (and treated as \"not using\") for respondents who said they "
        "never had.",
        "\"Are you currently doing something or using any method to delay or "
        "avoid (your wife) getting pregnant?\" Only asked of respondents not "
        "currently pregnant.",
        sources=[
            "field `current_use`, `label`/`hint` columns — `1_formative_research/"
            "table_analysis/data/1_raw/Ha-Fr_Collecte de Données sur le "
            "Terrain.xlsx`, sheet `survey`; relevance condition on field `ever_use`.",
            "field `fpbeh_fpnow`, `label` column — `2_phone pulse/meta/"
            "Participants_Appels de Suivi.xlsx`, sheet `survey`; relevance "
            "condition on field `current_pregnant`.",
        ],
    )
    st.caption(
        "Note the reference period differs: baseline asks about the **last 6 "
        "months**, follow-up asks about **right now**. Someone who used a method "
        "in month 3 of the baseline window but stopped by the interview date "
        "would count as \"using\" at baseline under this wording.¹"
    )
    _footnotes([
        "field `current_use` hint vs. field `fpbeh_fpnow` label — same source "
        "citation as \"Survey questions asked\" above.",
    ])
    st.markdown("---")

    row = df.iloc[0]
    col1, col2, col3 = st.columns(3)
    col1.metric("Using FP at baseline", f"{row['using_baseline_pct']:.1f}%")
    col2.metric(
        "Using FP at follow-up", f"{row['using_pulse_pct']:.1f}%",
        delta=f"{row['using_pulse_pct'] - row['using_baseline_pct']:+.1f} pts",
    )
    col3.metric(
        "Started using / Stopped",
        f"{int(row['started_using_n'])} / {int(row['stopped_using_n'])}",
    )

    p_value = row.get("mcnemar_p_value")
    direction = row.get("direction", "")
    if pd.notna(p_value):
        sig_note = (
            f"Statistically significant (McNemar's exact test, p = {p_value:.4f})"
            if p_value < SIG_THRESHOLD else
            f"Not statistically significant (McNemar's exact test, p = {p_value:.4f})"
        )
        st.caption(f"{direction.capitalize() if direction else ''} — {sig_note}".strip(" —"))

    fig = go.Figure(go.Bar(
        x=[row["using_baseline_pct"], row["using_pulse_pct"]],
        y=["Baseline", "Follow-up"],
        orientation="h",
        marker_color=[FEM_TAUPE, FEM_NAVY],
        text=[f"{row['using_baseline_pct']:.1f}%", f"{row['using_pulse_pct']:.1f}%"],
        textposition="outside",
    ))
    fig.update_layout(
        **_CHART,
        title=row.get("question", "Currently using FP"),
        xaxis_title="% of linked respondents",
        xaxis_range=[0, 115],
        height=260,
        margin=dict(l=10, r=30, t=78, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "\"Started using\" = not using FP at baseline, using at follow-up. "
        "\"Stopped\" = the reverse."
    )


def _render_limitations() -> None:
    with st.expander("Limitations & caveats"):
        st.markdown(
            "- **Measurement effect**: the baseline was an in-person interview and "
            "the follow-up a phone call; the change in mode/privacy could shift "
            "reported answers on its own, independent of any real change.\n"
            "- **Linkage / attrition selection**: only 471 of 968 formative "
            "respondents (92.5% of the 509 reachable Phone Pulse respondents) were "
            "successfully linked across waves. If reachable/re-interviewed "
            "respondents differ systematically from those lost to follow-up, this "
            "comparison isn't necessarily representative of the full baseline sample.\n"
            "- **Confounding variables**: seasonal patterns, supply/stockout "
            "changes, or other health programming active over the same period "
            "could also contribute to the change shown here."
        )


def render() -> None:
    st.markdown("### Phone Pulse — Baseline vs Follow-up")

    with st.expander("How this comparison works", expanded=True):
        st.markdown(
            "- **Paired, not two separate samples.** Every \"baseline\" number on "
            "this page comes from the SAME 471 people¹ whose \"follow-up\" number "
            "sits next to it — the 471 respondents successfully linked, via a "
            "roster crosswalk, between the Formative Research baseline (968 "
            "respondents total)¹ and this Phone Pulse follow-up (509 respondents "
            "who passed QA)². The other 497 baseline respondents never appear on "
            "this page at all — not in the baseline % either.\n"
            "- **Why pairing matters**: because it's the same people at two "
            "points in time, the statistical tests used here (McNemar's exact "
            "test, Wilcoxon signed-rank) can ask \"did *this group's* answers "
            "change more than chance would predict\" — a question a comparison "
            "of two different samples couldn't answer.\n"
            "- **Different survey mode**: baseline was an in-person interview "
            "(mostly Hausa); follow-up is a phone call. See \"Survey questions "
            "asked\" in each tab below for the exact wording and known "
            "differences between the two."
        )
        st.markdown("---")
        _footnotes([
            "`3_linkage/outputs/match_report.txt` — 968 formative, 509 phone "
            "pulse, 471 linked (92.5% of phone pulse respondents).",
            "`2_phone pulse/etl_pipeline/outputs/population_summary.csv` — "
            "n_after_qa.",
        ])

    tab1, tab2 = st.tabs(["Method Awareness", "Current FP Use"])
    with tab1:
        _render_method_awareness()
        _render_limitations()
    with tab2:
        _render_fp_use()
        _render_limitations()
