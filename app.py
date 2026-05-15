import streamlit as st

from seed_portfolio import PORTFOLIO

st.title("Portivo — v0")
st.write("Built by Leon Kleinau")

total_invested = sum(
    p["purchase_price"] + p["kaufnebenkosten_total"] for p in PORTFOLIO
)
monthly_kaltmiete = sum(p["kaltmiete_monthly"] for p in PORTFOLIO)
n_properties = len(PORTFOLIO)

col1, col2, col3 = st.columns(3)
col1.metric("Total Invested", f"€{total_invested:,.0f}")
col2.metric("Monthly Kaltmiete", f"€{monthly_kaltmiete:,.0f}")
col3.metric("Properties", n_properties)

st.subheader("Portfolio")
st.dataframe(PORTFOLIO, use_container_width=True)
