import streamlit as st


def stub_card(title, description, fields):
    st.markdown(f"""
    <div style="background:#fafafa;border:1.5px dashed #d1d5db;border-radius:10px;padding:1.5rem;margin-bottom:1rem;">
        <p style="font-size:1rem;font-weight:600;color:#374151;margin:0 0 0.4rem;">{title} — pending data</p>
        <p style="color:#6b7280;margin:0 0 1rem;font-size:0.9rem;">{description}</p>
        <p style="color:#9ca3af;font-size:0.82rem;margin:0;"><strong>Expected data fields:</strong> {", ".join(fields)}</p>
    </div>
    """, unsafe_allow_html=True)


def render_phone_pulse_stub(page_name: str):
    """Benin hasn't fielded a phone pulse follow-up survey yet -- every
    Phone Pulse tab renders this until that data exists. See
    data_loader.py's "Phone Pulse pages" note."""
    st.header(f"Phone Pulse — {page_name}")
    st.caption("No phone pulse data has been collected for Benin yet.")
    stub_card(
        page_name,
        "This section will populate once a phone pulse follow-up survey is fielded and its "
        "ETL pipeline is built (mirroring niger_app/src/page_pp_*.py and pipeline_output's "
        "etl_pp_*.py modules, neither of which exist for Benin yet).",
        ["Depends on the specific phone pulse questionnaire design"],
    )
