import streamlit as st

from seed_portfolio import PORTFOLIO
from utils import euro, german_date, get_loan, get_property

st.title("Portivo")
st.caption("Portfolio-Übersicht")

resolved = [get_property(p["property_id"]) for p in PORTFOLIO]

total_invested = sum(
    p["purchase_price"] + p["kaufnebenkosten_total"] for p in resolved
)
monthly_kaltmiete = sum(p["kaltmiete_monthly"] for p in resolved)
n_properties = len(resolved)

col1, col2, col3 = st.columns(3)
col1.metric("Investiertes Kapital", euro(total_invested))
col2.metric("Kaltmiete pro Monat", euro(monthly_kaltmiete))
col3.metric("Wohnungen", n_properties)

st.divider()

st.subheader("Wohnungen")
st.caption("Klicke auf eine Adresse, um zur Detailansicht zu wechseln.")

for p in resolved:
    loan = get_loan(p["property_id"])
    with st.container(border=True):
        if st.button(
            p["address"],
            key=f"open_{p['property_id']}",
            type="tertiary",
            use_container_width=True,
        ):
            st.session_state["selected_property_id"] = p["property_id"]
            st.query_params["property_id"] = p["property_id"]
            st.switch_page("views/wohnung.py")

        cols = st.columns(5)
        with cols[0]:
            st.caption("Wohnfläche")
            st.write(f"**{p['wohnflaeche_sqm']} m²**")
        with cols[1]:
            st.caption("Kaufdatum")
            st.write(f"**{german_date(p['purchase_date'])}**")
        with cols[2]:
            st.caption("Kaufpreis")
            st.write(f"**{euro(p['purchase_price'])}**")
        with cols[3]:
            st.caption("Kaltmiete (mtl.)")
            st.write(f"**{euro(p['kaltmiete_monthly'])}**")
        with cols[4]:
            st.caption("Finanzierung")
            if loan:
                st.write(f"**{loan['bank']}**")
            else:
                st.write("⚠️ **Daten fehlen**")
